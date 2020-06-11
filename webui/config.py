import os
import secrets
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    secret_file = os.path.join(basedir, 'secret_key')
    try:
        with open(secret_file) as fd:
            SECRET_KEY = fd.read()
    except FileNotFoundError:
        SECRET_KEY = secrets.token_urlsafe(64)
        with open(secret_file, 'w') as fd:
            fd.write(SECRET_KEY)

    EXPORTS_DIR = 'exports'
    BOOTSTRAP_SERVE_LOCAL = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
