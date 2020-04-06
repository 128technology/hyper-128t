"""Class for conductor virtual machines."""
from lib.router import Router


class Conductor(Router):
    default_node_role = 'conductor'

    def deploy(self):
        """Customize deploy method."""
        super().deploy()
        for node in self.nodes:
            node.install_license()
            node.prepare_netconf()
