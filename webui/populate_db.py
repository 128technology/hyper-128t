#!venv/bin/python
import argparse
import yaml
from werkzeug.security import generate_password_hash

from app import db
from app.models import Cluster, Deployment, Role, Settings, Site, User


def parse_arguments():
    parser = argparse.ArgumentParser('Import data into database')
    parser.add_argument('--import-filename', '-i', default='data.yaml',
                        help='import filename')
    return parser.parse_args()


def main():
    args = parse_arguments()
    import_filename = args.import_filename

    # cleanup
    db.drop_all()
    db.create_all()

    data = yaml.safe_load(open(import_filename))

    settings = data.get('settings')
    if settings:
        s = Settings(**settings)
        db.session.add(s)
        db.session.commit()

    basic_user = Role(name="basic_user")
    db.session.add(basic_user)
    user_roles = {}

    for role in data.get('roles', []):
        r = Role(name=role['name'])
        if 'permissions' in role:
            r.permissions = role['permissions']
        db.session.add(r)
        for user in role['users']:
            user_roles[user] = r
    db.session.commit()

    for user in data.get('users', []):
        username = user['username']
        if 'password' in user:
            password_hash = generate_password_hash(user['password'])
        else:
            password_hash = user['password_hash']
        u = User(
            username=username,
            firstname=user['firstname'],
            lastname=user['lastname'],
            email=user['email'],
            password_hash=password_hash,
            role=basic_user,
        )
        if username in user_roles:
            u.role = user_roles[username]
        db.session.add(u)
        print(u, u.role)
    db.session.commit()

    cluster_deployments = {}
    for cluster in data.get('clusters', []):
        deployments = cluster['deployments']
        del(cluster['deployments'])
        c = Cluster(**cluster)
        for deployment in deployments:
            cluster_deployments[deployment] = c
        db.session.add(c)
        print(c)
    db.session.commit()
    #return

    for deployment in data.get('deployments', []):
        sites = deployment['sites']
        del(deployment['sites'])
        d = Deployment(**deployment)
        d.cluster = cluster_deployments[d.name]
        db.session.add(d)
        print(d.cluster)
        for site in sites:
             s = Site(name=site, deployment=d)
             print(s)
             db.session.add(s)
        print(d)
    db.session.commit()


if __name__ == '__main__':
    main()
