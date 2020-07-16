from flask import session

#from app.lib import get_settings
from app import lib
from app.models import Cluster, Deployment, Role, User


def get_selected_deployment():
    selected_deployment = session.get('selected_deployment')
    if selected_deployment:
        return Deployment.query.filter_by(name=selected_deployment).first()
    return None


def reset_selected_deployment():
    if 'selected_deployment' in session:
        del(session['selected_deployment'])


def get_context():
    context = {
        'clusters': Cluster.query.filter_by(is_deleted=False),
        'deployments': Deployment.query.filter_by(is_deleted=False),
        'roles': Role.query.all(),
        'settings': lib.get_settings(),
        'users': User.query.filter_by(is_deleted=False),
    }
    selected_deployment = get_selected_deployment()
    if selected_deployment:
        context['uncommitted_sites'] = [
            site for site in selected_deployment.sites
            if not (site.is_deleted or site.is_installed)]
        context['archieved_sites'] = [
            site for site in selected_deployment.sites
            if not site.is_deleted and site.is_installed]
    return context
