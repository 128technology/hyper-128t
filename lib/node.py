"""Class for virtual machine nodes."""
import json
from openssh_wrapper import SSHError
import time

from lib.log import debug, fatal
from lib.vm import VM


def generate_node_name(router_name, suffix):
    """Generate node name."""
    node_name = router_name
    if suffix:
        node_name = '{}-{}'.format(router_name, suffix)
    return node_name


class Node(VM):

    def __init__(self, router, hypervisor, suffix=''):
        self.router = router
        self.hypervisor = hypervisor
        self.suffix = suffix
        self.is_secondary = False
        self.set_parameters()

    def set_parameters(self):
        """Set parameters for templating."""
        self.role = self.router.default_node_role
        self.name = generate_node_name(self.router.name, self.suffix)
        self.fqdn = '{}.{}'.format(
            self.name, self.router.deployment.domain_name)
        self.template = self.router.deployment.config['reference_template']
        self.interfaces = self.router.parameters['interfaces']
        if self.suffix:
            self.interfaces = self.interfaces[self.suffix]
        self.set_ip_adresses()
        self.router.ip_adresses.append(self.ip_address)

        self.set_passwords(self.router.parameters['passwords'])
        self.set_ssh_keys(self.router.parameters['ssh_keys'])

    def install_license(self):
        """Copy license file to conductor."""
        self.run_ssh('mkdir /etc/pki/128technology')
        self.run_scp(self.router.deployment.license_file,
                     '/etc/pki/128technology/release.pem')

    def init_iso_instance(self):
        """Run commands to initialize cloned instance."""
        bash_history = 't128-salt-key -L\njournalctl -fu 128T\ncat /etc/salt/minion'
        commands = (
            'hostnamectl set-hostname {}'.format(self.fqdn),
            'systemctl stop getty@tty1.service',
            'rm -f /lib/systemd/system/getty@tty1.service.d/override.conf',
            'systemctl daemon-reload',
            'systemctl stop firewalld',
            'systemctl start getty@tty1.service',
            'echo "{}" > /root/.bash_history'.format(bash_history),
        )
        timeout = 20
        while True:
            try:
                ret = self.run_ssh('uptime')
                debug('Output of uptime:', ret)
                if ret.returncode == 0:
                    break
            except SSHError:
                debug('Running "uptime" has failed.',
                      'Waiting {} seconds.'.format(timeout))
            finally:
                # wait for ssh server to be ready
                time.sleep(timeout)
                if timeout >= 10:
                    timeout = int(timeout / 2)

        debug('Adjusting VM...')
        self.run_ssh(commands)

    def generate_t128_id_rsa(self):
        """Generate ssh key needed for initialize128t."""
        ret = self.run_ssh([
            'ssh-keygen -q -N "" -f /root/.ssh/t128_id_rsa',
            'cat /root/.ssh/t128_id_rsa.pub',
        ])
        self.t128_id_rsa_key = ret.stdout.decode('ascii')

    def set_initialize128t_parameters(self):
        """Define the parameters as needed by initialize128t."""
        self.init = {
            'router-name': self.router.name,
            'node-name': self.name,
            'node-role': self.role,
            'disable-roadrunner': True,
            'pdc-key-comment': self.fqdn,
            'admin-password': self.passwords['admin'],
        }
        if self.suffix:
            self.init['node-ip'] = self.ha_sync_ip_address
            self.init['ha-peer-ip'] = self.peer_node.ha_sync_ip_address
            self.init['ha-peer-name'] = self.peer_node.name
            if self.role == 'conductor' and self.is_secondary:
                self.init['learn-from-ha-peer'] = True
                # generate key for learn-from-ha-peer
                self.generate_t128_id_rsa()
                self.peer_node.run_ssh(
                    "echo '{}' >> /root/.ssh/authorized_keys".format(
                        self.t128_id_rsa_key))

        if self.role == 'combo':
            # Define conductors when initializing router nodes
            self.init['conductor'] = {}
            keys = ['primary', 'secondary']
            for i, ip in enumerate(self.router.deployment.conductor.ip_adresses):
                self.init['conductor'][keys[i]] = {'ip': ip}

    def initialize_128t(self):
        """Initialize 128T."""
        preferences_command = "echo '{}' > /root/128t_preferences.json".format(
            json.dumps(self.init))

        ret = self.run_ssh([
            preferences_command,
            'initialize128t -p /root/128t_preferences.json',
            'systemctl enable 128T',
            'systemctl start 128T',
        ])

    def change_passwords(self):
        """Change passwords of specified users."""
        commands = []
        for user, password in self.passwords.items():
            if user == 'admin':
                continue
            commands.append(
                'echo "{}:{}" | chpasswd -e'.format(user, password))
        ret = self.run_ssh(commands)

    def copy_ssh_keys(self):
        """Copy ssh keys for specified users."""
        commands = []
        for user, ssh_key in self.ssh_keys.items():
            commands.append(
                'mkdir ~{}/.ssh; echo "{}" >> ~{}/.ssh/authorized_keys'.format(
                    user, ssh_key, user))
        ret = self.run_ssh(commands)

    def retrieve_pdc_ssh_key(self):
        """Copy pdc pub key from 128T."""
        ret = self.run_ssh([
            'cat /etc/128technology/ssh/pdc_ssh_key.pub',
        ])
        self.pdc_ssh_key = ret.stdout.decode('ascii')

    def prepare_netconf(self):
        """Run commands in order to prepare the netconf interface."""
        # This should be triggered on conuctor nodes only
        if self.role != 'conductor':
            fatal('This method should not be triggered on routers.')

        # load ssh key for netconf - if not defined, fall back to root
        netconf_authorized_keys = self.ssh_keys.get('netconf')
        if not netconf_authorized_keys:
            netconf_authorized_keys = self.ssh_keys['root']

        ret = self.run_ssh([
            'while [ ! -s /home/admin/.ssh/netconf_authorized_keys ]; do sleep 5; done',
            'echo "{}" >> /home/admin/.ssh/netconf_authorized_keys'.format(
                netconf_authorized_keys)
        ])

    def deploy(self):
        """Deploy a node on the hypervisor."""
        debug('Deploying node:', self.name)
        success = self.hypervisor.deploy_vm(
            self, self.router.deployment.assume_yes)
        if success:
            self.set_initialize128t_parameters()
            self.initialize_128t()
            self.retrieve_pci_addresses()
            self.change_passwords()
            self.copy_ssh_keys()
            self.retrieve_pdc_ssh_key()
        return success
