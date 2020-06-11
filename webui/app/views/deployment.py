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
from app.lib import _render_template
from app.forms import DeploymentForm, LoginForm, SiteForm, SiteEditForm
from app.models import Cluster, Deployment, Role, Site, User
from app.templates import get_config_templates, get_template_variables, get_template_string_variables, TEMPLATE_DIR
from app.views.context import get_context, get_selected_deployment, reset_selected_deployment


TRASH_BIN = '<span class="glyphicon glyphicon-trash"></span>'


def get_deployments():
    return [deployment.to_dict() for deployment in Deployment.query.all()]


def get_db_site(site_name):
    return Site.query.filter_by(name=site_name, is_deleted=False).first()


@app.route('/deployment', methods=['GET', 'POST'])
@login_required
def create_deployment():
    # dynamically load new clusters
    class _DeploymentForm(DeploymentForm):
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
    # return redirect(url_for('index'))


@app.route('/deployment/<deployment_name>')
@login_required
def select_deployment(deployment_name):
    session['selected_deployment'] = deployment_name
    flash('Deployment {} selected'.format(deployment_name))
    return redirect(url_for('index'))


def populate_form_from_template(form, fields):
    for field in fields:
        setattr(form, field,
                StringField(validators=[DataRequired()]))


def get_site_form(selected_template):
    class SiteTemplateForm(SiteForm):
        name = StringField(
            'Site Name', validators=[DataRequired()],
            render_kw={'placeholder': 'e.g. name of the city', 'autofocus': True})

    templates = get_config_templates()
    form = SiteForm()

    if selected_template and selected_template in templates:
        # Create fields based on template variables
        populate_form_from_template(
            SiteTemplateForm, get_template_variables(selected_template))
        SiteTemplateForm.create = SubmitField('Create')
        form = SiteTemplateForm()
        form.template.default = selected_template
    else:
        # Set focus to template selection on blank form
        form.template.render_kw['autofocus'] = True

    return form


def get_site_edit_form(site_name):
    # Needed to be able to change the form definition
    class _SiteEditForm(SiteEditForm):
        pass

    site = get_db_site(site_name)
    if not site:
        abort(404)

    # Load template from backend and populate form fields based on template
    template_vars = []
    if site.template_content:
        template_string = gzip.decompress(
            base64.b64decode(site.template_content))
        template_vars = get_template_string_variables(template_string)
        populate_form_from_template(_SiteEditForm, template_vars)

    # Load data from backend into form
    data = {'template_name': site.template_name}
    if site.template_parameters:
        data.update(json.loads(site.template_parameters))

    if current_user.has_permission('site_update'):
        _SiteEditForm.update = SubmitField('Update Site')
    if current_user.has_permission('site_delete'):
         _SiteEditForm.commit = SubmitField('Commit to Conductor')
    if current_user.has_permission('site_delete'):
        _SiteEditForm.delete = SubmitField('Delete Site')

    form = _SiteEditForm(data=data)
    return form, template_vars


def get_template_parameters(form, template_vars):
    template_parameters = json.dumps(
        {k: getattr(form, k).data for k in template_vars})
    return template_parameters


@app.route('/site', methods=['GET', 'POST'])
@login_required
def create_site():
    selected_template = request.args.get('template')
    form = get_site_form(selected_template)
    if form.validate_on_submit():
        site_name = form.name.data
        template_name = form.template.data
        # The used template should be copied to the data backend
        # to ensure changes on the template file don't interfere
        # with the uncommitted site.
        # Upcoming edits are soley done on this stored template content
        with open(os.path.join(TEMPLATE_DIR, template_name), 'rb') as fd:
            template_content = base64.b64encode(
                gzip.compress(fd.read())).decode('ascii')

        template_vars = get_template_variables(template_name)
        site = Site(
            name=site_name,
            template_name=template_name,
            template_content=template_content,
            template_parameters=get_template_parameters(form, template_vars),
        )
        selected_deployment = get_selected_deployment()
        if selected_deployment:
            site.deployment = selected_deployment
        db.session.add(site)
        db.session.commit()
        flash('Site {} created'.format(form.name.data))
        audit_log('created site:', site_name, '|',
                  'template:', template_name, '|',
                  'data:', site.template_parameters)

        return redirect(url_for('edit_site', site_name=site_name))
    else:
        if form.errors:
            flash(form.errors)
    form.process()  # needed to send the "selected" option to html
    context = get_context()
    return _render_template(
        'generic_form.html', title='New Site', form=form, **context)


@app.route('/site/<site_name>', methods=['GET', 'POST'])
@login_required
def edit_site(site_name):
    form, template_vars = get_site_edit_form(site_name)
    if form.validate_on_submit():
        if 'delete' in form._fields.keys() and form.delete.data:
            return redirect(url_for('delete_site', site_name=site_name))
        if 'commit' in form._fields.keys() and form.commit.data:
            site = get_db_site(site_name)
            site.is_installed = True
            db.session.commit()
            flash('Site {} has been committed'.format(site_name))
            audit_log('has committed site', site_name)
            return redirect(url_for('view_site', site_name=site_name))
        if 'update' in form._fields.keys() and form.update.data:
            site = get_db_site(site_name)
            site.template_parameters = get_template_parameters(
                form, template_vars)
            audit_log('updated site:', site_name, '|',
                      'data:', site.template_parameters)
            db.session.commit()
            flash('Site {} has been updated'.format(site_name))

    context = get_context()
    return _render_template('generic_form.html',
                            title='Edit Site {}'.format(site_name),
                            form=form, **context)


@app.route('/view_site/<site_name>')
@login_required
def view_site(site_name):
    form, template_vars = get_site_edit_form(site_name)
    del(form.commit)
    del(form.update)
    for field in template_vars:
        getattr(form, field).render_kw = {'readonly': True}
    context = get_context()
    audit_log('viewed site', site_name)
    return _render_template('generic_form.html',
                            title='View Site {}'.format(site_name),
                            action='/site/{}'.format(site_name),
                            form=form, **context)


@app.route('/delete_site/<site_name>')
@login_required
def delete_site(site_name):
    site = get_db_site(site_name)
    site.is_deleted = True
    db.session.commit()
    audit_log('deleted site', site_name)
    flash('Site {} has been deleted'.format(site_name))
    return redirect(url_for('index'))
