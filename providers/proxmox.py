"""Virtual machines on Proxmox."""
from proxmoxer import ProxmoxAPI
from urllib.parse import quote

from lib.log import debug, fatal, info
from providers.hypervisor import Hypervisor


class Proxmox(Hypervisor):
    proxmox = None

    def init_api(self):
        self.proxmox = ProxmoxAPI(
            host=self.host,
            user=self.config['username'],
            password=self.config['password'])
        self.default_node = self.proxmox.nodes.get()[0]['node']

    def deploy_vm(self, instance, assume_yes):
        """Deploy a VM on the given hypervisor."""
        if not self.proxmox:
            self.init_api()
            #fatal('No proxmox connection')

        proxmox = self.proxmox
        node = self.default_node

        # find template id among all vms on the hypervisor node
        vm_ids = []
        template_id = None
        template = instance.template
        for vm in proxmox.nodes(node).qemu.get():
            if vm['name'] == template and vm['template']:
                template_id = vm['vmid']
            vm_ids.append(int(vm['vmid']))
        if not template_id:
            fatal('Template could not be found on: {}.'.format(self.host))

        # find next free vm id starting at 100
        new_id = 100
        for id in sorted(vm_ids):
            if id == new_id:
                new_id += 1

        info('Creating a new VM:\n * ID: {}\n * Name: {}\n * Host: {}'.format(
            new_id, instance.name, self.host))
        if not assume_yes:
            yn = input('Continue [yN]? ')
            if yn != 'y' and yn != 'Y':
                return False
        t = proxmox.nodes(node).qemu(template_id)
        info('VM is being created. This may take some time...')
        debug('Cloning template...')
        c = t.clone.create(newid=new_id, name=instance.name)

        ssh_key = instance.ssh_keys['root']
        ssh_key_quoted = quote(ssh_key, safe='')

        adjustments = {
            # remove cdrom drive if any
            'delete': 'ide2',
            # set cloud-init options
            'cipassword': instance.passwords['root'],
            'ciuser': 'root',
            'sshkeys': ssh_key_quoted,
        }
        # network parameters
        i = 0
        for interface, details in instance.interfaces.items():
            ipconfig = 'ip={ip_address}/{ip_prefix}'.format(**details)
            if 'gateway' in details:
                ipconfig += ',gw={}'.format(details['gateway'])
            adjustments['ipconfig{}'.format(i)] = ipconfig
            i += 1
        # remove mpls interface from conductors
        if instance.role == 'conductor':
            adjustments['delete'] += ',net2'

        proxmox.nodes(node).qemu(new_id).config.set(**adjustments)
        debug('Starting VM...')
        proxmox.nodes(node).qemu(new_id).status.start.post()
        instance.init_iso_instance()
        return True


Hypervisor = Proxmox
