from datetime import datetime
from flask_login import UserMixin
import json
import os
from sqlalchemy_utils import IPAddressType
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app import lib
from app import login
from app import templates


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    opencage_key = db.Column(db.String(32))
    config_highlight_color = db.Column(db.String(50))
    default_tls_cert = db.Column(db.Text)

    def to_dict(self):
        d = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if not value:
                continue
            if key in ('id',):
                continue
            d[key] = value
        return d


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    firstname = db.Column(db.String(64))
    lastname = db.Column(db.String(64))
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    is_deleted = db.Column(db.Boolean, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.username)

    def __list_name__(self):
        return '{} {} ({})'.format(self.firstname, self.lastname, self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        d = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if key in ('id', 'role_id', 'role'):
                continue
            d[key] = value
        return d

    def has_permission(self, permission):
        # admins have all permissions
        if self.role is Role.query.filter_by(name='admin').first():
            return True
        permission_json = self.role.permissions
        if permission_json:
            permission_strings = json.loads(permission_json)
            if type(permission) is str:
                return permission in permission_strings
            if type(permission) in [tuple, list]:
                return any([p in permission_strings for p in permission])
        return False


class Role(db.Model):
    # PERMISSIONS_CHOICES = {}
    PERMISSIONS = (
       'user_management',
       'role_management',
       'cluster_management',
       'export_data',
       'purge_objects',
       'change_settings',
       'deployment_select',
       'deployment_create',
       'deployment_read',
       'deployment_update',
       'deployment_delete',
       'deployment_commit',
       'site_create',
       'site_read',
       'site_update',
       'site_delete',
       'site_commit',
    )
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    users = db.relationship('User', backref='role', lazy=True)
    permissions = db.Column(db.String)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.name)

    def to_dict(self):
        d = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if key == 'id':
                continue
            d[key] = value
        d['users'] = [user.username for user in self.users]
        return d


class Deployment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, unique=True)
    short_name = db.Column(db.String(32), index=True, unique=True)
    domain_name = db.Column(db.String(128))
    location = db.Column(db.String(128))
    high_available = db.Column(db.Boolean, default=True)
    conductor_ip_address_1 = db.Column(IPAddressType)
    conductor_ip_address_2 = db.Column(IPAddressType)
    admin_password = db.Column(db.String(64))
    root_password = db.Column(db.String(64))
    t128_password = db.Column(db.String(64))
    root_ssh_key = db.Column(db.String(512))
    t128_ssh_key = db.Column(db.String(512))
    config_template = db.Column(db.String(64))
    is_installed = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'))
    sites = db.relationship('Site', backref='deployment', lazy=True)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.name)

    def __list_name__(self):
        return self.name

    def to_dict(self):
        d = {}
        for key, value in tuple(self.__dict__.items()):
            if key.startswith('_'):
                continue
            if key == 'id':
                continue
            if key in ('conductor_ip_address_1', 'conductor_ip_address_2'):
                d[key] = str(value)
                continue
            if not value:
                continue
            d[key] = value
            d['sites'] = [site.to_dict() for site in self.sites]
        return d


class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    template_name = db.Column(db.String(512))
    #template_content = db.Column(db.Text)
    template_parameters = db.Column(db.Text)
    msr_parameters = db.Column(db.Text)
    is_installed = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    deployment_id = db.Column(db.Integer, db.ForeignKey('deployment.id'))
    __table_args__ = (db.UniqueConstraint('deployment_id', 'name'),)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.name)

    def __list_name__(self):
        return '{} (Deployment: {})'.format(
            self.name, self.deployment.__list_name__())

    def to_dict(self):
        d = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if key in ('id', 'deployment_id'):
                continue
            if not value:
                continue
            d[key] = value
        return d

    def get_template_parameters(self):
        return json.loads(self.template_parameters)

    def get_msr_parameters(self):
        return json.loads(self.msr_parameters)

    def get_text_config(self, parameters, template_string=None):
        conductor_ips = [str(self.deployment.conductor_ip_address_1)]
        if self.deployment.conductor_ip_address_2:
            conductor_ips.append(str(self.deployment.conductor_ip_address_2))
        parameters['_deployment_name_'] = self.deployment.name
        parameters['_deployment_short_name_'] = self.deployment.short_name
        parameters['_site_name_'] = self.name
        parameters['conductor_ips'] = conductor_ips
        if not template_string:
            template_string = templates.get_template_content(self.template_name)
        text_config = templates.get_rendered_template(template_string, parameters)
        return text_config, conductor_ips

    def commit(self, callback_success, callback_error):
        parameters = self.get_template_parameters().copy()
        parameters.update(self.get_msr_parameters())

        text_config, conductor_ips = self.get_text_config(parameters)

        # fallback if no deployment key can be found
        identity_file = 'netconf_ssh_key'
        deployment_key = '../ssh_keys/{}'.format(self.deployment.name.lower())
        if os.path.isfile(deployment_key):
            identity_file = deployment_key

        return lib.commit_config(
            conductor_ips,
            identity_file,
            text_config,
            callback_success,
            callback_error,
        )


class Cluster(db.Model):
    PROVIDER_CHOICES = {
       1: 'promox',
       2: 'aws',
    }
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    provider = db.Column(db.Integer)
    host1 = db.Column(db.String(256))
    host2 = db.Column(db.String(256))
    password = db.Column(db.String(64))
    is_deleted = db.Column(db.Boolean, default=False)
    deployments = db.relationship('Deployment', backref='cluster', lazy=True)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.name)

    def __list_name__(self):
        return self.name

    def to_dict(self):
        d = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if not value:
                continue
            if key in ('id',):
                continue
            if key == 'provider':
                d[key] = value
                continue
            d[key] = value
        d['deployments'] = [deployment.name for deployment in self.deployments]
        return d


class SSHKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    pubkey = db.Column(db.String(512))
    is_deleted = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.name)

    def __list_name__(self):
        return self.name

    def to_dict(self):
        d = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if not value:
                continue
            if key in ('id',):
                continue
            d[key] = value
        d['deployments'] = [deployment.name for deployment in self.deployments]
        return d


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
