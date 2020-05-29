"""Class for 128T deployments."""
import os

from lib.conductor import Conductor
from lib.log import fatal, info
from lib.router import Headend
from lib.providers import get_provider


class Deployment(object):

    def __init__(self, config, parameters, assume_yes=False):
        self.config = config
        self.parameters = parameters
        self.assume_yes = assume_yes
        self.set_parameters()
        self.load_hypervisors()
        self.branches = []

    def set_parameters(self):
        """Set parameters for templating."""
        self.name = self.parameters['deployment_name']
        self.license_file = self.parameters['license_file']
        if not os.path.isfile(self.license_file):
            fatal('License file "{}" could not be found.'.format(
                self.license_file))
        self.domain_name = self.parameters['domain_name']
        self.high_available = self.parameters.get('high_available', False)

    def load_hypervisors(self):
        """Load hypervisors as configured."""
        provider = get_provider(self.config['provider'])
        self.hypervisors = []
        for index, host in enumerate(self.config.get('hypervisors')):
            hypervisor = provider.Hypervisor(self.config, host, index+1)
            self.hypervisors.append(hypervisor)

        # TODO: subset selection to be implemented
        # (round-robin, random, most resources, ...)
        # specify the hypervisors for the conductor
        self.hypervisors_conductor = self.hypervisors
        # specify the hypervisors for the headend
        self.hypervisors_headend = self.hypervisors

    def set_conductor(self, hypervisors, suffixes):
        """Helper."""
        conductor = Conductor(self, hypervisors, suffixes)
        self.conductor = conductor

    def set_headend(self, hypervisors, suffixes):
        """Helper."""
        headend = Headend(self, hypervisors, suffixes)
        self.headend = headend

    def create(self):
        """Create a deployment with all configured conductors and routers."""
        suffixes = ['a', 'b']
        self.set_conductor(self.hypervisors_conductor, suffixes)
        self.conductor.create()
        info('Conductor IP address(es):', ' '.join(self.conductor.ip_adresses))

        if 'headend' in self.parameters:
            self.set_headend(self.hypervisors_headend, suffixes)
            self.headend.create()
        #branch = Branch(self)
        #self.branches.append(branch)
