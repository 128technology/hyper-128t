from config import Config
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_url_path='/static')
app.config.from_object(Config)
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)

login = LoginManager(app)
login.login_view = 'login'

from app.views import deployment
from app.views import export
from app.views import generic
from app.views import user
