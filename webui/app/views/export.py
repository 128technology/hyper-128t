from datetime import datetime
from flask import Response
from flask_login import current_user, login_required
import os
import yaml

from app import app
from app.audit import audit_log
from app.lib import get_settings, permission_required
from app.models import Cluster, Role, User
from app.views.deployment import get_deployments_dict


def get_users_dict():
    return [user.to_dict() for user in User.query.all()]


def get_roles_dict():
    return [role.to_dict() for role in Role.query.all()
            if role.name != 'basic_user']


def get_clusters_dict():
    return [cluster.to_dict() for cluster in Cluster.query.all()]


def get_settings_dict():
    return get_settings().to_dict()


@app.route('/export')
@login_required
@permission_required('export_data')
def export():
    data = {
        'settings': get_settings_dict(),
        'users': get_users_dict(),
        'roles': get_roles_dict(),
        'deployments': get_deployments_dict(),
        'clusters': get_clusters_dict(),
    }
    content = yaml.dump(data)
    filename = 'export-hyper-128t-webui-{}-{:%Y-%m-%d_%H-%M-%S}.yaml'.format(
        current_user.username, datetime.now())
    audit_log('requested a data export')
    export_dir = app.config.get('EXPORTS_DIR')
    if not os.path.isdir(export_dir):
        os.mkdir(export_dir)
    with open(os.path.join(export_dir, filename), 'w') as fd:
        fd.write(content)
    return Response(
        content,
        mimetype='text/yaml',
        headers={'Content-disposition':
                 'attachment; filename={}'.format(filename)})
    return redirect(url_for('index'))
