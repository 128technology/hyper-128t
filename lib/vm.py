"""Base class for 128T virtual machines."""
from collections import OrderedDict
import json
from openssh_wrapper import SSHConnection, SSHError
import os
from passlib.hash import sha512_crypt
from subprocess import check_call, check_output, CalledProcessError

from lib.log import debug, fatal


def get_ssh_conn(ip_address, login='root', identity_file=None):
    """Return ssh connection."""
    configfile = 'ssh_config'
    if not os.path.isfile(configfile):
        configfile = None
    return SSHConnection(ip_address, login=login, configfile=configfile,
                         identity_file=identity_file)


def scp_down(ip_address, source_file, destination_file, identity_file=None):
    """Download a file over ssh."""
    with open(destination_file, 'wb') as fd:
        conn = get_ssh_conn(ip_address, identity_file=identity_file)
        ret = conn.run('cat {}'.format(source_file))
        fd.write(ret.stdout)


def address_to_ip_prefix(address):
    """Convert address to ip and prefix."""
    return address.split('/')


class VM(object):

    def set_name(self, suffix):
        """Set instance name."""
        self.router_name, self.node_name = generate_node_name(
            self.deployment_name, self.role, suffix)

    def set_ip_adresses(self):
        """Set ip addresses of all interfaces."""
        # unfold a config tree for the current suffix, if any
        for interface, details in self.interfaces.items():
            for k, v in details.items():
                if k == 'address':
                    ip, prefix = address_to_ip_prefix(v)
                    self.interfaces[interface]['ip_address'] = ip
                    self.interfaces[interface]['ip_prefix'] = prefix
                    break
            if interface == 'wan':
                self.ip_address = ip
            if interface == 'ha_sync':
                self.ha_sync_ip_address = ip

    def set_passwords(self, passwords):
        """Convert cleartext passwords to hashes."""
        self.passwords = {}
        for user_name in passwords:
            self.passwords[user_name] = sha512_crypt.hash(
                passwords[user_name], rounds=5000)

    def set_ssh_keys(self, ssh_keys):
        """Load ssh public keys from file if needed."""
        self.ssh_keys = {}
        self.ssh_keys_private = {}
        for user_name in ssh_keys:
            key = ssh_keys[user_name]
            if key.startswith('file:'):
                public_key_file = key.split('file:')[1]
                with open(public_key_file) as fd:
                    key = fd.read()
                # try to open private key
                private_key_file = public_key_file.split('.pub')[0]
                try:
                    with open(private_key_file) as fd:
                        self.ssh_keys_private[user_name] = private_key_file
                except FileNotFoundError:
                    pass

            self.ssh_keys[user_name] = key.strip()
            if user_name == 'root':
                # check if the private key is available:
                # (1) check ssh-agent
                # (2) check for private key file
                command = "echo {} | ssh-keygen -l -f - | awk '{{ print $2 }}'"
                finger = check_output(command.format(self.ssh_keys[user_name]),
                                      shell=True, encoding='ascii')
                try:
                    command = 'ssh-add -l | grep -q {}'
                    check_call(command.format(finger), shell=True)
                    return
                except CalledProcessError:
                    if user_name not in self.ssh_keys_private:
                        fatal('Could not find matching ssh key for root -',
                              'neither in ssh-agent nor on disk.')

    def run_ssh(self, commands):
        """Run ssh commands on virtual machine."""
        identity_file = self.ssh_keys_private.get('root')
        conn = get_ssh_conn(self.ip_address, identity_file=identity_file)
        if type(commands) not in (tuple, list):
            commands = [commands]
        for command in commands:
            ret = conn.run(command)
            if ret.returncode != 0:
                debug('Running command has failed:', command)
                debug('stdout:', ret.stdout)
                debug('stderr:', ret.stderr)
        return ret

    def run_scp(self, source, target, mode='0644', owner='root:'):
        """Run scp commands to virtual machine."""
        identity_file = self.ssh_keys_private.get('root')
        conn = get_ssh_conn(self.ip_address, identity_file=identity_file)
        conn.scp((source, ), target=target, mode=mode, owner=owner)

    def retrieve_pci_addresses(self):
        """Retrieve pci addresses for network interfaces."""
        debug('Retrieve PCI addresses...')
        try:
            lshw_json = self.run_ssh('lshw -json').stdout
        except SSHError:
            fatal('Cannot connect to node:', self.ip_address)
        lshw = json.loads(lshw_json)
        pci_addresses = []
        for component in lshw["children"][0]["children"]:
            if component["class"] == "bridge":
                for subsystem in component["children"]:
                    if subsystem["class"] == "network":
                        index = int(subsystem["id"].split(':')[1])
                        pci_addresses.append((index, subsystem["businfo"]))
        pci_addresses = [v.strip('pci@') for k,     v in sorted(pci_addresses)]
        # iterate over interfaces and set pci address
        i = 0
        for interface in self.interfaces:
            self.interfaces[interface]['pci_address'] = pci_addresses[i]
            i += 1
            if i >= len(pci_addresses):
                break
