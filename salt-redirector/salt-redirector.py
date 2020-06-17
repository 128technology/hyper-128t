#!venv/bin/python3

import flask
from flask import request, jsonify

import yaml

import salt.config
import salt.wheel
import salt.runner
import salt.client

opts = salt.config.master_config('/etc/salt/master')
wheel = salt.wheel.WheelClient(opts)
runner = salt.runner.RunnerClient(opts)
client = salt.client.LocalClient()

from jinja2 import Environment, FileSystemLoader, meta
from jinja2.exceptions import TemplateNotFound
import os

FLASK_DIR = 'flask_pages'

def _load_environment():
    return Environment(loader=FileSystemLoader(FLASK_DIR))

conductors = {}
with open('conductors.yml') as fd:
    conductors = yaml.load(fd, Loader=yaml.BaseLoader)

app = flask.Flask(__name__)
app.config['DEBUG'] = True

@app.route('/', methods=['GET'])
def display_minions():
    jj = _load_environment()
    context = {}
    context['conductors'] = list(conductors.keys())
    key_states = wheel.cmd('key.list_all')
    context['key_states'] = key_states
    connected_minions = runner.cmd('manage.up')
    context['connected_minions'] = connected_minions
    page_template = jj.get_template('minions.j2')
    return page_template.render(context)

@app.route('/accept/', methods=['POST'])
def accept_minion():
    minion = request.form.get('minion')
    wheel.cmd('key.accept', [minion])
    return "Accepted Salt Key for minion {}".format(minion)

@app.route('/delete/', methods=['POST'])
def delete_minion():
    minion = request.form.get('minion')
    wheel.cmd('key.delete', [minion])
    return "Salt Key for minion {} deleted".format(minion)

@app.route('/redirect/', methods=['POST'])
def redirect_minion():
    minion = request.form.get('minion')
    conductor_name = request.form.get('conductor')
    ret = client.cmd(minion, 
              'state.apply', 
              ['redirect', 
               "pillar={{'conductor':{}}}".format(conductors[conductor_name])
              ])
    print(ret)
    return "Attempting to redirect {} to conductor {}".format(minion, conductor_name)

app.run(host='0.0.0.0')
