#!venv/bin/python
from app import db
from app.models import Deployment, Role, Site, User
import yaml
from werkzeug.security import generate_password_hash


def main():
    db.drop_all()
    db.create_all()

    data = yaml.safe_load(open('data.yaml'))

    basic_user = Role(name="basic_user")
    db.session.add(basic_user)
    user_roles = {}
    for role in data['roles']:
        r = Role(name=role['rolename'])
        if 'permissions' in role:
            r.permissions = role['permissions']
        db.session.add(r)
        for user in role['users']:
            user_roles[user] = r
    db.session.commit()

    for user in data['users']:
        username = user['username']
        u = User(
            username=username,
            firstname=user['firstname'],
            lastname=user['lastname'],
            email=user['email'],
            password_hash=generate_password_hash(user['password']),
            role=basic_user,
        )
        if username in user_roles:
            u.role = user_roles[username]
        db.session.add(u)
        print(u, u.role)
    db.session.commit()

    for deployment in data['deployments']:
        d = Deployment(name=deployment['name'])
        db.session.add(d)
        for site in deployment['sites']:
            s = Site(name=site, deployment=d)
            print(s)
            db.session.add(s)
        print(d)
    db.session.commit()


if __name__ == '__main__':
    main()
