from flask import flash, redirect, url_for
from flask_login import login_required
import json
from werkzeug.security import generate_password_hash

from app import app
from app import db
from app.audit import audit_log
from app.forms import RoleCreateForm, RoleEditForm, UserCreateForm, UserEditForm
from app.lib import _render_template, permission_required
from app.models import Role, User
from app.views.context import get_context


def change_user(form, user, action):
    # store seleted role to add it properly to the user object later
    role = Role.query.filter_by(name=form.role.data).first()
    if form.password.data:
        password_hash = generate_password_hash(form.password.data)
        user.password_hash = password_hash
    del form.role
    del form.password
    form.populate_obj(user)
    user.role = role
    db.session.add(user)
    db.session.commit()
    flash('User {} {}'.format(user.username, action))
    audit_log(action, 'user', user.username)
    return redirect(url_for('index'))


@app.route('/user', methods=['GET', 'POST'])
@login_required
@permission_required('user_management')
def create_user():
    form = UserCreateForm()
    if form.validate_on_submit():
        user = User()
        return change_user(form, user, 'created')
    context = get_context()
    return _render_template(
        'generic_form.html', title='New User', form=form, **context)


@app.route('/user/<user_name>', methods=['GET', 'POST'])
@login_required
@permission_required('user_management')
def edit_user(user_name):
        form = UserEditForm()
        user = User.query.filter_by(username=user_name).first()
        if form.validate_on_submit():
            if form.update.data:
                return change_user(form, user, 'updated')
            if form.delete.data:
                return redirect(url_for('delete_user', user_name=user.username))

        form = UserEditForm(obj=user)
        form.role.data = user.role.name
        context = get_context()
        return _render_template(
            'generic_form.html', title='Edit User', form=form, **context)


@app.route('/delete_user/<user_name>')
@login_required
@permission_required('user_management')
def delete_user(user_name):
    user = User.query.filter_by(username=user_name).first()
    user.is_deleted = True
    db.session.commit()
    action = 'deleted'
    flash('User {} {}'.format(user.username, action))
    audit_log(action, 'user', user.username)
    return redirect(url_for('index'))


@app.route('/role', methods=['GET', 'POST'])
@login_required
@permission_required('role_management')
def create_role():
    form = RoleCreateForm()
    if form.validate_on_submit():
        role = Role(permissions=json.dumps(form.permissions.data))
        del form.permissions
        form.populate_obj(role)
        db.session.add(role)
        db.session.commit()
        flash('Role {} created'.format(form.name.data))
        audit_log('created role', role.name)
        return redirect(url_for('index'))
    context = get_context()
    return _render_template(
        'generic_form.html', title='New Role', form=form, **context)


@app.route('/role/<role_name>', methods=['GET', 'POST'])
@login_required
@permission_required('role_management')
def edit_role(role_name):
    role = Role.query.filter_by(name=role_name).first()
    form = RoleEditForm(obj=role)

    # remove disabled keyword from previous calls
    try:
        del form.permissions.render_kw['disabled']
    except KeyError:
        pass

    if form.validate_on_submit():
        permissions = json.dumps(form.permissions.data)
        del form.permissions
        form.populate_obj(role)
        role.permissions = permissions
        db.session.add(role)
        db.session.commit()
        flash('Role {} updated'.format(form.name.data))
        audit_log('updated role', role.name)
        return redirect(url_for('index'))

    # populate permissions multi selector based on db field (json string)
    if role.permissions:
        form.permissions.data = json.loads(role.permissions)
    if role.name == 'admin':
        form.permissions.render_kw['disabled'] = 'disabled'
    context = get_context()
    return _render_template(
        'generic_form.html', title='Edit Role', form=form, **context)
