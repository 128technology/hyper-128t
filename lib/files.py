"""Helper module for file handling."""
from collections import OrderedDict
import json
import yaml

from lib.log import fatal


def read_json(filename):
    """Read a json file and return its data in python data structure."""
    with open(filename) as fd:
        try:
            return json.load(fd)
        except json.decoder.JSONDecodeError:
            fatal('File is not in JSON format:', filename)


def ordered_yaml_load(stream):
    """Load yaml contents ordered."""
    class OrderedLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def read_yaml(filename):
    """Read a yaml file and return its data in python data structure."""
    with open(filename) as fd:
        try:
            return ordered_yaml_load(fd)
        except yaml.parser.ParserError:
            fatal('File is not in YAML format:', filename)
