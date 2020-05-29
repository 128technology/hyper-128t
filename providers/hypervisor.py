"""Abstract base class for hypervisors."""


class Hypervisor(object):

    def __init__(self, config, host, index):
        self.config = config
        self.host = host
        self.index = index
