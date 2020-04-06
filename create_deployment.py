"""Create a virtual 128T deployment on a given hypervisor."""

from lib.argparse import common_parser, parse_config, parse_parameters
from lib.config import read_config
from lib.deployment import Deployment
from lib.log import debug, set_log_level
from lib.parameters import read_parameters, validate_parameters


def parse_arguments():
    """Get commandline arguments."""
    parser = common_parser(
        description='Create 128T deployment in virtualized infrastructure.')
    parser = parse_config(parser)
    parser = parse_parameters(parser)
    return parser.parse_args()


def main():
    """Call all functions needed to create a deployment."""
    args = parse_arguments()
    log_level = 'INFO'
    if args.debug:
        log_level = 'DEBUG'
    set_log_level(log_level)

    config = read_config(args.config_file)
    parameters = read_parameters(args.parameters_file)
    validate_parameters(parameters)
    deployment = Deployment(config, parameters, assume_yes=args.assumeyes)
    deployment.create()


if __name__ == '__main__':
    main()
