import base64
from datetime import datetime
from flask import abort, flash, redirect, render_template, request, session, url_for, Response
from flask_login import current_user, login_required, login_user, logout_user
import json
import gzip
import os
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import yaml

from app import app
from app import db
from app.audit import audit_log
from app.lib import _render_template, flash_error, address_to_coordinates, flash_success, deployment_required, permission_required, process_form
from app.forms import DeploymentCreateForm, DeploymentEditForm, LoginForm, SiteForm, SiteEditForm
from app.models import Cluster, Deployment, Role, Site, User
from app.templates import get_config_templates, get_template_variables, get_template_string_variables, get_template_content
from app.views.context import get_context, get_selected_deployment, reset_selected_deployment


TRASH_BIN = '<span class="glyphicon glyphicon-trash"></span>'


def get_deployments_dict():
    return [deployment.to_dict() for deployment in Deployment.query.all()]


def selected_deployment(deployment_name):
    if selected_deployment not in session or \
            deployment_name != session['selected_deployment']:
        session['selected_deployment'] = deployment_name
        flash('Deployment {} selected'.format(deployment_name))


def get_db_deployment(deployment_name):
    return Deployment.query.filter_by(
        name=deployment_name, is_deleted=False).first()


def get_db_site(site_name):
    return Site.query.filter_by(
        name=site_name,
        deployment=get_selected_deployment(),
        is_deleted=False
    ).first()


def change_deployment(form, deployment, action):
    # store seleted cluster to add it properly to the user object later
    #cluster = Cluster.query.filter_by(name=form.cluster.data).first()
    cluster = Cluster.query.filter_by().first()
    #del form.cluster
    form.populate_obj(deployment)
    deployment.cluster = cluster
    db.session.add(deployment)
    db.session.commit()
    flash('Deployment {} {}'.format(deployment.name, action))
    audit_log(action, 'deployment', deployment.name)


@app.route('/deployment', methods=['GET', 'POST'])
@login_required
def create_deployment():
    # dynamically load new clusters
    class _DeploymentForm(DeploymentCreateForm):
        pass
    _DeploymentForm.cluster.kwargs['choices'] = sorted(list(set(
        _DeploymentForm.cluster.kwargs['choices'] +
        [(c.id, c.name) for c in Cluster.query.all()])))

    # when a new deploment is created, unselect a previous one
    reset_selected_deployment()

    form = _DeploymentForm()
    if form.validate_on_submit():
        deployment = Deployment(cluster=Cluster.query.get(form.cluster.data))
        del form.cluster
        form.populate_obj(deployment)
        db.session.add(deployment)
        db.session.commit()
        session['selected_deployment'] = deployment.name
        flash('Deployment {} created'.format(form.name.data))
        audit_log('created deployment', deployment.name)
        return redirect(url_for('index'))
    context = get_context()
    return _render_template(
        'generic_form.html', title='New Deployment', form=form, **context)


@app.route('/deployment/<deployment_name>', methods=['GET', 'POST'])
@login_required
@permission_required('deployment_select')
def edit_deployment(deployment_name):
    # Select deployment if needed
    selected_deployment(deployment_name)
    if not current_user.has_permission(('deployment_read',
                                        'deployment_update',
                                        'deployment_delete')):
            return redirect(url_for('index'))

    # dynamically load new clusters
    # class _DeploymentEditForm(DeploymentEditForm):
    #     pass
    # _DeploymentEditForm.cluster.kwargs['choices'] = sorted(list(set(
    #     _DeploymentEditForm.cluster.kwargs['choices'] +
    #     [(c.id, c.name) for c in Cluster.query.all()])))

    deployment = get_db_deployment(deployment_name)
    # form = _DeploymentEditForm(obj=deployment)
    form = DeploymentEditForm()
    print('validate_on_submit:', form.validate_on_submit())

    # form = _DeploymentEditForm(data={'cluster': 1})
    # form.cluster.default = 1
    # form.process()
    # #form.process(obj=deployment)
    # print('form.cluster.data:', form.cluster.data)
    # print('form.cluster.default:', form.cluster.default)
    # # # if not form.cluster.data:
    # # #form.cluster.data = (deployment.cluster.id, deployment.cluster.name)
    # print('deployment.cluster:', deployment.cluster)
    from pprint import pprint
    pprint(form.__dict__)
    print('CSRF:', form.csrf_token)
    # if form.is_submitted():
    #     print("submitted")
    # if form.validate():
    #     print("valid")
    if form.validate_on_submit():
        if form.update.data:
            change_deployment(form, deployment, 'updated')
        if form.delete.data:
            return redirect(url_for('delete_deployment', deployment_name=deployment.name))

    else:
        #form = _DeploymentEditForm(obj=deployment)
        form = DeploymentEditForm(obj=deployment)
    context = get_context()
    return _render_template(
        'generic_form.html', title='Edit Deployment', form=form, **context)


def get_template_parameters(form, template_vars):
    template_parameters = json.dumps(
        {k: getattr(form, k).data for k in template_vars})
    return template_parameters


def keep_fields(form, fields):
    for field in list(form._fields):
        if field in fields:
            continue
        form.__delattr__(field)


def remove_buttons(form, buttons):
    for field in list(form._fields):
        if field in buttons:
            form.__delattr__(field)


def populate_form_from_template(form, data, fields, msr_parameters):
    """Add form fields based on template variables."""
    # dynamic helper class
    class _Form(form.__class__):
        pass

    # add fields as strings to form
    for field in sorted(fields):
        render_kw = {}
        if field in msr_parameters:
            render_kw['readonly'] = True
        if field == 'gps_coordinates':
            render_kw['ondblclick'] = 'open_map(this)'
        setattr(_Form, field, StringField(render_kw=render_kw))

    _form = _Form(data=data)

    # msr_data override form data
    _form.msr_data.data = data['msr_data']
    _form.msr_data.render_kw = {'rows': min(len(msr_parameters), 10)}
    # _form.msr_data.render_kw = {'rows': min(len(msr_parameters), 10), 'onpaste': 'paste_msr(this)'}
    for field, value in msr_parameters.items():
        try:
            getattr(_form, field).data = value
        except AttributeError:
            pass

    # move submit buttons to end of the form
    for name, field in _form._fields.copy().items():
        if isinstance(field, SubmitField):
            _form._fields.move_to_end(name)
    return _form


def parse_msr_data(msr_data):
    msr_parameters = {}
    if msr_data:
        for line in msr_data.splitlines():
            cols = line.split('!')[0].split(':')
            if len(cols) >= 2:
                key, value = cols[:2]
                key = key.strip().replace('-', '_')
                msr_parameters[key] = value.strip()
    return msr_parameters


def process_site_form(form, site_name, context):
    selected_template = None
    site = None
    if site_name:
        # edit database object
        site = get_db_site(site_name)

        # take template from object
        try:
            selected_template = site.template_name
        except AttributeError:
            pass

    if form.template.data and selected_template != form.template.data:
        # take template from form (if changed)
        selected_template = form.template.data

    if selected_template:
        # modify form based on selected template
        template_vars = get_template_variables(selected_template)

        data = {'template': selected_template}
        if site:
            # prepare object data that can be loaded into dynamic form
            data['name'] = site.name
            if site.template_parameters:
                data.update(site.get_template_parameters())
            if site.msr_parameters:
                msr_parameters = site.get_msr_parameters()

        if form.msr_data.data is not None:
            msr_parameters = parse_msr_data(form.msr_data.data)
        # use msr_data as form defaults
        data.update(msr_parameters)

        # write back cleaned data into form field
        data['msr_data'] = '\n'.join(
            ['{}: {}'.format(*i) for i in msr_parameters.items()])

        if 'gps_coordinates' in template_vars and not data.get('gps_coordinates'):
            address = ''
            if 'address' in template_vars and data.get('address'):
                address = data.get('address')

            address_elements = []
            for key in ('inst_zip', 'inst_town', 'inst_street'):
                value = msr_parameters.get(key, '')
                if value:
                    address_elements.append(value)
            composite_address = ' '.join(address_elements)

            if not address and composite_address:
                address = composite_address

            if address:
                coordinates = address_to_coordinates(address)
                if coordinates:
                    msr_parameters['gps_coordinates'] = coordinates

        form = populate_form_from_template(
            form, data, template_vars, msr_parameters)

        if site:
            # show config preview
            parameters = {}
            for name, field in form._fields.items():
                if name in template_vars:
                    parameters[name] = field.data
            template_string = get_template_content(selected_template)
            template_string = template_string.replace(
                '{{', '<span class="template_variable">{{').replace(
                '}}', '}}</span>')
            context['text_config'], _ = site.get_text_config(
                parameters, template_string)

            remove_buttons(form, ('create'))

            if site.is_installed:
                for field in form._fields.values():
                    field.render_kw = {'readonly': True}
                remove_buttons(form, ('update', 'commit'))

        else:
            remove_buttons(form, ('update', 'commit', 'delete'))
            site = Site(deployment=get_selected_deployment())

        if form.validate_on_submit():
            site.name = form.name.data
            site.template_name = form.template.data
            site.template_parameters = get_template_parameters(
                form, template_vars)
            site.msr_parameters = json.dumps(msr_parameters)
        #form.process()  # needed to send the "selected" option to html
    else:
        # if template is unspecified show only template selector
        keep_fields(form, ('csrf_token', 'template'))
        # Set focus to template selection on blank form
        form.template.render_kw['autofocus'] = True

    return form, site


def commit_site(site):
    return site.commit(flash_success, flash_error)


@app.route('/site', methods=['GET', 'POST'])
@app.route('/site/<site_name>', methods=['GET', 'POST'])
@login_required
@deployment_required
def handle_site(site_name=None):
    return process_form(process_site_form, commit_site, SiteForm(), site_name)
