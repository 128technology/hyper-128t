from datetime import datetime
from flask import Response
from flask_login import current_user, login_required
import os
import yaml

from app import app
from app.audit import audit_log
from app.lib import permission_required
from app.models import Cluster, Role, User
from app.views.deployment import get_deployments


def get_users():
    return [user.to_dict() for user in User.query.all()]


def get_roles():
    return [role.to_dict() for role in Role.query.all()
            if role.name != 'basic_user']


def get_clusters():
    return [cluster.to_dict() for cluster in Cluster.query.all()]


@app.route('/export')
@login_required
@permission_required('export_data')
def export():
    data = {
        'users': get_users(),
        'roles': get_roles(),
        'deployments': get_deployments(),
        'clusters': get_clusters(),
    }
    content = yaml.dump(data)
    filename = 'export-hyper-128t-webui-{}-{:%Y-%m-%d_%H-%M-%S}.yaml'.format(
        current_user.username, datetime.now())
    audit_log('requested a data export')
    with open(os.path.join(app.config.get('EXPORTS_DIR'), filename), 'w') as fd:
        fd.write(content)
    return Response(
        content,
        mimetype='text/yaml',
        headers={'Content-disposition':
                 'attachment; filename={}'.format(filename)})
    return redirect(url_for('index'))
