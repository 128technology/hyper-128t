"""Base class for 128T virtual machines."""
from collections import OrderedDict
import json
from openssh_wrapper import SSHConnection, SSHError
import os
from passlib.hash import sha512_crypt

from lib.log import debug, fatal


def get_ssh_conn(ip_address, login='root'):
    """Return ssh connection."""
    cf = 'ssh_config'
    if not os.path.isfile(cf):
        cf = None
    return SSHConnection(ip_address, login=login, configfile=cf)


def scp_down(ip_address, source_file, destination_file):
    """Download a file over ssh."""
    with open(destination_file, 'wb') as fd:
        conn = get_ssh_conn(ip_address)
        ret = conn.run('cat {}'.format(source_file))
        fd.write(ret.stdout)


def address_to_ip_prefix(address):
    """Convert address to ip and prefix."""
    return address.split('/')


class VM(object):
    name = 'unknown'
    hypervisor = None
    passwords = {}
    ip_config = OrderedDict()
    ssh_keys = {}

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
        for user_name in passwords:
            self.passwords[user_name] = sha512_crypt.hash(
                passwords[user_name], rounds=5000)

    def set_ssh_keys(self, ssh_keys):
        """Load ssh public keys from file if needed."""
        for user_name in ssh_keys:
            if user_name == 'jdoe':
                continue
            key = ssh_keys[user_name]
            if key.startswith('file:'):
                with open(key.split('file:')[1]) as fd:
                    key = fd.read()
            self.ssh_keys[user_name] = key.strip()

    def run_ssh(self, commands):
        """Run ssh commands on virtual machine."""
        conn = get_ssh_conn(self.ip_address)
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
        conn = get_ssh_conn(self.ip_address)
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
        pci_addresses = [v.strip('pci@') for k,v in sorted(pci_addresses)]
        # iterate over interfaces and set pci address
        i = 0
        for interface in self.interfaces:
            self.interfaces[interface]['pci_address'] = pci_addresses[i]
            i += 1
            if i >= len(pci_addresses):
                break
