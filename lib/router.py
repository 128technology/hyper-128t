"""Class for 128T routers."""
import json
import tempfile

from lib.log import debug, info
from lib.node import Node
from lib.vm import scp_down

import lib.config_template as ct
from lib.configurator import t128ConfigHelper
from ncclient.operations.rpc import RPCError
from lib.ote_utils.netconfutils.netconfconverter import ConfigParseError


def generate_router_name(deployment_name, role):
    """Generate router name."""
    router_name = '{}-{}'.format(deployment_name, role)
    return router_name


class NoNodeDeployedException(BaseException):
    pass


class Router(object):
    default_node_role = 'combo'

    def __init__(self, deployment, hypervisors, suffixes):
        self.deployment = deployment
        self.hypervisors = hypervisors
        self.suffixes = suffixes
        self.set_parameters()
        self.ip_adresses = []
        self.prepare()

    def set_parameters(self):
        """Set parameters for templating."""
        self.role = self.__class__.__name__.lower()
        self.name = generate_router_name(self.deployment.name, self.role)
        self.parameters = self.deployment.parameters[self.role]
        self.gps = self.parameters.get('gps')
        self.location = self.parameters.get('location')
        self.config_template = self.parameters.get('config_template')
        self.passwords = self.parameters.get('passwords')
        self.ssh_keys = self.parameters.get('ssh_keys')
        self.shared_mac_addresses = self.parameters.get('shared_mac_addresses')

    def prepare(self):
        """Create a router with its nodes."""
        debug('Creating {}:'.format(self.role), self.name)
        self.nodes = []
        for hypervisor in self.hypervisors:
            if self.deployment.high_available:
                suffix = self.suffixes[self.hypervisors.index(hypervisor)]
                self.nodes.append(Node(self, hypervisor, suffix))
            else:
                self.nodes.append(Node(self, hypervisor))
                break

        for i, node in enumerate(self.nodes):
            if len(self.nodes) == 2:
                node.peer_node = self.nodes[(i+1) % 2]
                if i == 1:
                    node.is_secondary = True

    def sync_pdc_ssh_keys(self):
        """Sync public keys between nodes."""
        pdc_ssh_keys = '\n'.join([node.pdc_ssh_key for node in self.nodes])
        copy_cmd = "echo '{}' > /etc/128technology/ssh/authorized_keys".format(
            pdc_ssh_keys)
        for node in self.nodes:
            node.run_ssh(copy_cmd)

    def deploy(self):
        """Deploy the nodes on hypervisors."""
        success = False
        for node in self.nodes:
            success |= node.deploy()
        if not success:
            raise NoNodeDeployedException()

        self.sync_pdc_ssh_keys()

    def configure(self):
        conductor_netconf_ip = self.deployment.conductor.ip_adresses[0]
        context = {}
        context['router'] = self
        context['deployment'] = self.deployment

        try:
            t128_model = tempfile.NamedTemporaryFile()
            scp_down(
                conductor_netconf_ip,
                '/var/model/consolidatedT128Model.xml',
                t128_model.name)
            text_config = ct.get_text_config(context, self.config_template)
            with open('audit/{}.cfg'.format(self.name), 'w') as fd:
                fd.write(text_config)
            xml_config = ct.get_xml_config(text_config, t128_model)
        except ConfigParseError as e:
            info("There was an error in the config: {}".format(e))
            return False

        try:
            with t128ConfigHelper(host=conductor_netconf_ip) as ch:
                edit_status = ch.edit(xml_config, 'conductor timeout error')
        except RPCError as e:
            info("There was an error in the config: {}".format(e))
            return False

        if isinstance(edit_status, str):
            info(edit_status)

        if edit_status.ok:
            with t128ConfigHelper(host=conductor_netconf_ip) as ch:
                try:
                    commit_status = ch.commit()
                except RPCError as e:
                    info("There was an error committing the configuration, please check the candidate config: {}".format(e))
                    return False
                if commit_status.ok:
                    info("Configuration committed successfully")
                    return True
                else:
                    info("There was an error committing the config")
                    return False
        else:
            info("There was an error adding the candidate config")
            return False

    def create(self):
        """Create a new router."""
        try:
            self.deploy()
            self.configure()
        except NoNodeDeployedException:
            info('No', self.role, 'node has been deployed.')


class Headend(Router):
    """Class for headend routers."""


class Branch(Router):
    """Class for branch routers."""
