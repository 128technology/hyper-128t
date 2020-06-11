# ONLY FOR DEBUGGING
from bs4 import BeautifulSoup
from flask import abort, render_template
from flask_login import current_user
from functools import wraps


def _render_template(*args, **kwargs):
    html = render_template(*args, **kwargs)
    return BeautifulSoup(html, 'html.parser').prettify()


def permission_required(permission_name):
    """Define a decorator similar to 'login_required' in order to check
       if the current_user is allowed to use the wrapped function."""
    def real_decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if not current_user.has_permission(permission_name):
                abort(403)
            retval = function(*args, **kwargs)
            return retval
        return wrapper
    return real_decorator
