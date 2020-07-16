from collections import OrderedDict

from flask_wtf import FlaskForm
import wtforms
from wtforms import BooleanField, FieldList, FormField, PasswordField, SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms import Form
from wtforms.validators import DataRequired, Email, EqualTo, InputRequired, IPAddress, Required

from app.models import Cluster, Deployment, Role, Site
from app.templates import get_config_templates


class SettingsForm(FlaskForm):
    opencage_key = StringField(
        render_kw={
            'placeholder': '1234567890abcdef1234567890abcdef',
            # 'data_toggle': 'tooltip',
            # 'data_placement': 'left',
            # 'title': 'For details about OpenCage Geocoder see: <a href="https://opencagedata.com/">https://opencagedata.com/</a>',
        },
    )
    config_highlight_color = StringField(
        filters=[lambda v: '#28a745' if v == '' else v],
        render_kw={'placeholder': '#28a745'},
    )
    update = SubmitField()


class LoginForm(FlaskForm):
    username = StringField(
        validators=[InputRequired()],
        render_kw={'placeholder': 'Username', 'autofocus': True})
    password = PasswordField(
        validators=[InputRequired()], render_kw={'placeholder': 'Password'})
    submit = SubmitField('Log in')


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('',
        validators=[InputRequired()],
        render_kw={'placeholder': 'Current password'})
    new_password = PasswordField('', validators=[
            InputRequired(),
            EqualTo('new_password_confirm', message='Passwords must match')],
        render_kw={'placeholder': 'New password'})
    new_password_confirm = PasswordField('',
        validators=[InputRequired()],
        render_kw={'placeholder': 'Confirm new password'})
    submit = SubmitField('Change Password')


class UserForm(FlaskForm):
    username = StringField(validators=[DataRequired()],
        render_kw={'autofocus': True})
    firstname = StringField(validators=[DataRequired()])
    lastname = StringField(validators=[DataRequired()])
    email = StringField(validators=[DataRequired(), Email()])
    role = SelectField(
        choices=[('', '--- Please select role ---')],
        validators=[DataRequired()],
    )

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.role.choices.extend(
            [(role.name, role.name) for role in Role.query.all()])
        self.role.choices.sort()


class UserCreateForm(UserForm):
    password = PasswordField(validators=[InputRequired()])
    create = SubmitField()


class UserEditForm(UserForm):
    password = PasswordField()
    update = SubmitField()
    delete = SubmitField()


class RoleForm(FlaskForm):
    name = StringField(validators=[DataRequired()],
        render_kw={'placeholder': 'Role name', 'autofocus': True})
    permissions = SelectMultipleField(
        choices=[(i, i) for i in Role.PERMISSIONS],
        render_kw={'size': len(Role.PERMISSIONS)},
    )


class RoleCreateForm(RoleForm):
    create = SubmitField()


class RoleEditForm(RoleForm):
    update = SubmitField()


class ClusterForm(FlaskForm):
    name = StringField(validators=[DataRequired()],
        render_kw={'placeholder': 'Cluster name', 'autofocus': True})
    provider = SelectField(
        choices=Cluster.PROVIDER_CHOICES.items(),
        coerce=int,
    )
    host1 = StringField('Hypervisor Host #1', validators=[DataRequired()])
    host2 = StringField('Hypervisor Host #2')
    password = StringField('Hypervisor Password', validators=[DataRequired()])


class ClusterCreateForm(ClusterForm):
    create = SubmitField()


class ClusterEditForm(ClusterForm):
    update = SubmitField()


class PurgeForm(FlaskForm):
    purge = SubmitField()


class SiteForm(FlaskForm):
    template = SelectField(
        choices=[('', '--- Please select template ---')] +
                [(template, template) for template in get_config_templates()],
        validators=[DataRequired()],
        render_kw={'onchange': 'load_template()'})
    name = StringField(
        'Site Name', validators=[DataRequired()],
        render_kw={'placeholder': 'e.g. name of the city', 'autofocus': True})
    msr_data = TextAreaField('MSR Data',
                             render_kw={'onpaste': 'paste_msr()'})
    create = SubmitField('Create Site')
    update = SubmitField('Update Site')
    commit = SubmitField('Commit to Conductor')
    delete = SubmitField('Delete Site')


class DeploymentForm(FlaskForm):
    name = StringField(validators=[DataRequired()],
        render_kw={'placeholder': 'Deployment name', 'autofocus': True})
    short_name = StringField()
    # cluster = SelectField(
    #     choices=[(0, '--- Please select cluster ---')],
    #     # choices=[(0, '--- Please select cluster ---')] +
    #     #         [(c.id, c.name) for c in Cluster.query.all()],
    #     validators=[DataRequired()],
    #     coerce=int,
    # )
    # domain_name = StringField(validators=[DataRequired()],
    #                           render_kw={'placeholder': 'sdwan.plusnet.de'})
    # location = StringField(
    #     render_kw={'placeholder': 'Mathias-Brüggen-Str. 55, 50829 Köln'})
    #high_available = BooleanField(default=True, render_kw={'onchange': 'enable_ha(this)'})
    #high_available = BooleanField(default=True)
    conductor_ip_address_1 = StringField(
        'Conductor IP Address #1', validators=[InputRequired(), IPAddress()])
    # conductor_ip_address_2 = StringField(
    #     'Conductor IP Address #2', validators=[IPAddress()])
    conductor_ip_address_2 = StringField('Conductor IP Address #2')
    #admin_password = StringField('admin Password', validators=[DataRequired()])
    #root_password = StringField('root Password', validators=[DataRequired()])
    #t128_password = StringField('t128 Password', validators=[DataRequired()])
    #deploy = BooleanField(default=True)
    #is_installed = BooleanField()
    #root_ssh_key = StringField()
    #t128_ssh_key = StringField()
    # config_template = SelectField(
    #     choices=[('', '--- Please select template ---')] +
    #             [(template, template) for template in get_config_templates()],
    #     validators=[DataRequired()],
    # )


class DeploymentCreateForm(DeploymentForm):
    create = SubmitField()
    create_deploy = SubmitField('Create & Deploy')

class DeploymentEditForm(DeploymentForm):
    deploy = SubmitField()
    update = SubmitField()
    delete = SubmitField()


class SiteEditForm(FlaskForm):
    template_name = StringField('Template', render_kw={'readonly': True})
