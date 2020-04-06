"""Helper module for common command line arguments."""
import argparse


def common_parser(description=None):
    """Get commandline arguments."""
    parser = argparse.ArgumentParser(description)
    parser.add_argument('--assumeyes', '-y', action='store_true',
                        help='answer yes for all questions')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='show debug messages')
    return parser


def parse_config(parser):
    """Add a argparse argument for config files."""
    parser.add_argument('--config-file', '-c', help='config filename',
                        default='config.yaml')
    return parser


def parse_parameters(parser):
    """Add a argparse argument for parameters files."""
    parser.add_argument('--parameters-file', '-p', help='parameter filename',
                        required=True)
    return parser
