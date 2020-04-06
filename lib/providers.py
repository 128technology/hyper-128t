"""Helper module to handle provider modules."""
import importlib


def get_provider(provider):
    """Load provider as configured."""
    try:
        module = importlib.import_module('providers.' + provider)
        return module
    except:
        raise
