from flask import flash, redirect, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash
from werkzeug.urls import url_parse

from app import app
from app import db
from app.audit import audit_log
from app.forms import ClusterCreateForm, ClusterEditForm, ClusterForm, LoginForm, PasswordChangeForm, PurgeForm, SettingsForm
from app.lib import _render_template, get_settings, permission_required, process_form
from app.models import Cluster, Deployment, Role, Site, User
from app.views.context import get_context, reset_selected_deployment


@app.route('/')
@login_required
def index():
    context = get_context()
    return _render_template('index.html', title='Home', **context)


def process_settings_form(form, name, context):
    class _Form(form.__class__):
        pass
    settings = get_settings()
    form = _Form(obj=settings)
    if form.validate_on_submit():
        form.populate_obj(settings)
    return form, settings


@app.route('/settings', methods=['GET', 'POST'])
@permission_required('change_settings')
@login_required
def handle_settings():
    return process_form(process_settings_form, None, SettingsForm())


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(
            username=form.username.data, is_deleted=False).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user)
        audit_log('logged in')
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return _render_template('login.html', title='Login - Hyper-128T', form=form)


@app.route('/logout')
@login_required
def logout():
    reset_selected_deployment()
    audit_log('logged out')
    logout_user()
    return redirect(url_for('login'))


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        error = ''
        if not current_user.check_password(form.current_password.data):
            error = 'Current password is not correct'
        if form.new_password.data != form.new_password_confirm.data:
            error = 'New passwords do not match'
        if not error:
            current_user.password_hash = generate_password_hash(
                form.new_password.data)
            db.session.commit()
            flash('Your password has been changed successfully')
            audit_log('changed password')
            return redirect(url_for('index'))
        flash(error, 'danger')
    context = get_context()
    return _render_template('generic_form.html', title='Change Password',
                            form=form, form_type='basic', **context)


@app.route('/cluster', methods=['GET', 'POST'])
@login_required
@permission_required('cluster_management')
def create_cluster():
    form = ClusterCreateForm()
    if form.validate_on_submit():
        cluster = Cluster()
        form.populate_obj(cluster)
        db.session.add(cluster)
        db.session.commit()
        flash('Cluster {} created'.format(form.name.data))
        audit_log('created cluster', cluster.name)
        return redirect(url_for('index'))
    context = get_context()
    return _render_template(
        'generic_form.html', title='New Cluster', form=form, **context)


@app.route('/cluster/<cluster_name>', methods=['GET', 'POST'])
@login_required
@permission_required('cluster_management')
def edit_cluster(cluster_name):
    cluster = Cluster.query.filter_by(name=cluster_name).first()
    form = ClusterEditForm(obj=cluster)
    if form.validate_on_submit():
        form.populate_obj(cluster)
        db.session.add(cluster)
        db.session.commit()
        flash('Cluster {} updated'.format(form.name.data))
        audit_log('updated cluster', cluster.name)
        return redirect(url_for('index'))
    context = get_context()
    return _render_template(
        'generic_form.html', title='Edit Cluster', form=form, **context)


@app.route('/purge', methods=['GET', 'POST'])
@login_required
@permission_required('purge_objects')
def purge():
    form = PurgeForm()
    objects = {}
    objects['Sites'] = list(Site.query.filter_by(is_deleted=True))
    objects['Deployments'] = list(Deployment.query.filter_by(is_deleted=True))
    objects['Users'] = list(User.query.filter_by(is_deleted=True))
    num_objects = sum([len(v) for k, v in objects.items()])
    if form.validate_on_submit():
        for l in objects.values():
            for item in l:
                db.session.delete(item)
        db.session.commit()
        return redirect(url_for('index'))
    context = get_context()
    return _render_template('purge.html', title='Purge Deleted Objects',
                            form=form, deleted_objects=objects,
                            num_objects=num_objects, **context)

# @app.route('/map/<coordinates>')
# @login_required
# def show_map(coordinates):
#     if coordinates.startswith('+'):
#         latitude = ''
#         coordinates = coordinates[1:]
#     if coordinates.startswith('-'):
#         latitude = '-'
#         coordinates = coordinates[1:]
#     coordinates = coordinates.strip('/').replace('+', ',').replace('-', ',-')
#     coordinates = '{}{}'.format(latitude, coordinates)
#     return _render_template('map.html', coordinates=coordinates)
