# ONLY FOR DEBUGGING
from bs4 import BeautifulSoup
from flask import abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user
from functools import wraps
from opencage.geocoder import OpenCageGeocode, NotAuthorizedError

from app import db
from app.models import Settings
from app.views.context import get_context

# needed to commit config to conductor
import os, sys, inspect
cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(cwd)
grant_parent_dir = os.path.dirname(parent_dir)
sys.path.insert(0, grant_parent_dir)
import lib.config_template as ct
from lib.configurator import t128ConfigHelper
from ncclient.operations.rpc import RPCError
from lib.ote_utils.netconfutils.netconfconverter import ConfigParseError


def _render_template(*args, **kwargs):
    html = render_template(*args, **kwargs)
    return BeautifulSoup(html, 'html.parser').prettify()


def flash_error(message):
    flash(message, 'danger')


def flash_success(message):
    flash(message)


def deployment_required(func):
    """Define a decorator similar to 'login_required' in order to check
       if a deployment has been selected."""
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if ('selected_deployment' not in session):
            flash_error('No deployment has been selected.')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return decorated_view


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


def commit_config(conductor_ips, identity_file, text_config,
                  callback_success, callback_error):
    """Commit a config to conductor."""
    conductor_netconf_ip = conductor_ips[0]
    #template_parameters['conductor_ips'] = conductor_ips
    try:
#             t128_model = tempfile.NamedTemporaryFile()
#             scp_down(
#                 conductor_netconf_ip,
#                 '/var/model/consolidatedT128Model.xml',
#                 t128_model.name,
# #                login='admin',
#                 identity_file=identity_file)
        open('/tmp/text.cfg', 'w').write(text_config)
        print('text_config:', text_config)
        t128_model = 'consolidatedT128Model.xml'
        xml_config = ct.get_xml_config(text_config, t128_model)
    except ConfigParseError as e:
        callback_error("There was an error in the config: {}".format(e))
        return False

    try:
        print('conductor_ip:', type(conductor_netconf_ip))
        with t128ConfigHelper(host=conductor_netconf_ip, username='admin',
                              key_filename=identity_file) as ch:
            edit_status = ch.edit(xml_config, 'conductor timeout error')
    except RPCError as e:
        callback_error("There was an error in the config: {}".format(e))
        return False

    if isinstance(edit_status, str):
        info(edit_status)

    if edit_status.ok:
        with t128ConfigHelper(host=conductor_netconf_ip, username='admin',
                              key_filename=identity_file) as ch:
            try:
                commit_status = ch.commit()
            except RPCError as e:
                callback_error("There was an error committing the configuration, please check the candidate config: {}".format(e))
                return False
            if commit_status.ok:
                callback_success("Configuration committed successfully")
                return True
            else:
                callback_error("There was an error committing the config")
                return False
    else:
         callback_error("There was an error adding the candidate config")
         return False



def get_action(form):
    for action in ('create', 'update', 'commit', 'delete'):
        if (hasattr(form, action) and
                getattr(form, action) and
                getattr(form, action).data):
            return action
    return None


def log_action(obj, action):
    action_string = action + 'd'
    if action == 'commit':
        action_string = 'committed'

    class_name = obj.__class__.__name__
    if hasattr(obj, 'name'):
        message = '{} {} has been {}'.format(class_name, obj.name, action_string)
    else:
        message = '{} has been {}'.format(class_name, action_string)
    #audit_log('deleted site', site_name)
    flash(message)


def process_form(callback, commit_hook, form, name=None):
    context = get_context()

    form, obj = callback(form, name, context)
    form_name = form.__class__.__name__
    if form_name.startswith('_'):
        form_name = form.__class__.__bases__[0].__name__
    entity = form_name.replace('Form', '')

    if obj:
        title = 'Edit {}'.format(entity)
        if hasattr(obj, 'name'):
            title = '{}: {}'.format(title, obj.name)
    else:
        title = 'New {}'.format(entity)

    if form.validate_on_submit():
        action = get_action(form)
        if action == 'create':
            db.session.add(obj)
            db.session.commit()
            log_action(obj, action)
            # redirect to edit page after object has been created
            return redirect('{}/{}'.format(request.path, obj.name))
        if action == 'update':
            db.session.commit()
            log_action(obj, action)

        if action == 'commit':
            success = commit_hook(obj)
            if success:
                obj.is_installed = True
                db.session.commit()
                log_action(obj, action)
                return redirect('{}'.format(request.path))
        if action == 'delete':
            obj.is_deleted = True
            db.session.commit()
            log_action(obj, action)
            return redirect(url_for('index'))

    return _render_template(
        'generic_form.html', title=title, form=form, **context)


def get_settings():
    try:
        settings = Settings.query.all()[0]
    except IndexError:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
        settings = Settings.query.all()[0]
    return settings


def to_iso6709(latitude, longitude):
    """Convert latitude and longitude to ISO 6709 format."""
    return '{:+f}{:+012.7f}/'.format(latitude, longitude)


def get_coordinates(place):
    """Get coordinates from OpenCageGeocode."""
    geocoder = OpenCageGeocode(API_KEY)
    return geocoder.geocode(
        place, limit=1, countrycode='de')[0]["geometry"].values()


def address_to_coordinates(address):
    """Convert address to iso6709."""
    settings = get_settings()
    if settings.opencage_key:
        try:
            geocoder = OpenCageGeocode(settings.opencage_key)
            latitude, longitude = geocoder.geocode(
                address, limit=1, countrycode='de')[0]["geometry"].values()
            return to_iso6709(latitude, longitude)
        except NotAuthorizedError:
            return None
