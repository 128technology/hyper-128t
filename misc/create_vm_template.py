#!/usr/bin/env python3

# allow to run the script from 'misc' directory
import sys
sys.path.append('.')

from datetime import datetime
from proxmoxer import ProxmoxAPI
from simple_term_menu import TerminalMenu
import time

from lib.argparse import common_parser, parse_config, parse_parameters
from lib.config import read_config
from lib.log import debug, fatal, info, set_log_level

TEMPLATE_NAME = '{:%Y%m%d}-128t-template-{}'
DEFAULTS = {
    'cores': 4,
    'cpu': 'host',
    'memory': '8192',
    'net0': 'e1000,bridge=vmbr0',
    'net1': 'e1000,bridge=vmbr1',
    'ostype': 'l26',
    'scsi0': 'local-lvm:64',
    'scsihw': 'virtio-scsi-pci',
    'start': '1',
}


def parse_arguments():
    """Get commandline arguments."""
    parser = common_parser(
        description='Create proxmox template for 128T virtual machines.')
    parser = parse_config(parser)
    return parser.parse_args()


def get_free_vmid(proxmox, node, base):
    vm_ids = []
    for vm in proxmox.nodes(node).qemu.get():
        vm_ids.append(int(vm['vmid']))

    # find next free vm id starting at 999 downwards
    new_id = base + 999
    for id in sorted(vm_ids, reverse=True):
        if id == new_id:
            new_id -= 1
    return new_id


def get_iso_image(proxmox, node):
    iso_images = []
    iso_images_display = []
    for iso in proxmox.nodes(node).storage.local.content.get(content='iso'):
        vol_id = iso.get('volid')
        if vol_id.startswith('local:iso/128T-') and 'cloudinit' in vol_id:
            iso_images.append(vol_id)
            iso_images_display.append(vol_id.replace('local:iso/', ''))

    terminal_menu = TerminalMenu(iso_images_display)
    choice = terminal_menu.show()
    return iso_images[choice]


def main():
    """Call all functions needed to create a deployment."""
    args = parse_arguments()
    log_level = 'INFO'
    if args.debug:
        log_level = 'DEBUG'
    set_log_level(log_level)

    config = read_config(args.config_file)
    for index, host in enumerate(config.get('hypervisors')):
        node = ''
        if ':' in host:
            host, node = host.split(':')
        proxmox = ProxmoxAPI(
            host=host,
            user=config['username'],
            password=config['password'],
            verify_ssl=config.get('verify_ssl', True))
        nodes = [d['node'] for d in proxmox.nodes.get()]
        if node:
            if node not in nodes:
                fatal('Specified node {} not configured on host {}'.format(
                    host, node))
            default_node = node
        else:
            default_node = nodes[0]
        new_id = get_free_vmid(proxmox, default_node, (index+1)*1000)
        iso_image = get_iso_image(proxmox, default_node)
        version = iso_image.replace(
            'local:iso/128T-', '').replace(
            '-cloudinit.x86_64.iso', '')
        template_name = TEMPLATE_NAME.format(datetime.now(), version)
        info('Creating a new template:\n * ID: {}\n * Name: {}\n * Host: {}'.format(
             new_id, template_name, host))
        if not args.assumeyes:
            yn = input('Continue [yN]? ')
            if yn != 'y' and yn != 'Y':
                continue

        vm_options = DEFAULTS.copy()
        if 'vm_options' in config:
            vm_options.update(config['vm_options'])
        vm_options['vmid'] = new_id
        vm_options['name'] = template_name
        vm_options['ide2'] = iso_image + ',media=cdrom'
        proxmox.nodes(default_node).qemu.create(**vm_options)

        vm = proxmox.nodes(default_node).qemu(new_id)
        info('Waiting until vm is stopped.')
        running = True
        while running:
            print('.', end='', flush=True)
            time.sleep(30)
            status = vm.status.current().get().get('status')
            running = (status == 'running')
        print('')
        info('VM has been stopped.')
        info('Adding CloudInit.')
        vm.config.set(ide0='local:cloudinit')
        vm.config.set(delete='ide2')
        info('Migrating to template.')
        vm.template().post()


if __name__ == '__main__':
    main()
