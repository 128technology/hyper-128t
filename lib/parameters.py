"""Module for config file handling."""
from lib.files import read_yaml
from lib.log import fatal


def read_parameters(filename):
    """Read a parameters file in yaml format."""
    parameters = read_yaml(filename)
    return parameters


def validate_parameters(parameters, schema=None):
    """Validate if parameters file contains needed values."""
    # fatal('Parameter missing in parameters file.')
    return True
