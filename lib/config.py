"""Module for config file handling."""
from lib.files import read_yaml


def read_config(filename):
    """Read a config file in yaml format."""
    config = read_yaml(filename)
    return config
