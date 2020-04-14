#!venv/bin/python3

import flask
from flask import request, jsonify
import lib.config_template as ct
from lib.configurator import t128ConfigHelper

from jinja2 import Environment, FileSystemLoader, meta
from jinja2.exceptions import TemplateNotFound
import os
from ncclient.operations.rpc import RPCError
from lib.ote_utils.netconfutils.netconfconverter import ConfigParseError

FLASK_DIR = 'flask_pages'

def _load_environment():
  return Environment(loader=FileSystemLoader(FLASK_DIR))

app = flask.Flask(__name__)
app.config['DEBUG'] = True

@app.route('/api/v1/list_templates', methods=['GET'])
def api_list_templates():
    return jsonify(ct.list_config_templates())

@app.route('/api/v1/get_template_variables', methods=['GET'])
def api_get_template_variables():
    if 'template' in request.args:
        template_name = request.args['template']
    else:
        return "ERROR: Template name not provided"

    vars = list(ct.show_template_variables(template_name))
    return jsonify(vars)

@app.route('/', methods=['GET'])
def display_templates():
    jj = _load_environment()
    templates = ct.list_config_templates()
    context = {}
    context['templates'] = templates
    page_template = jj.get_template('list_templates.j2')
    return page_template.render(context)

@app.route('/fill_template', methods=['GET'])
def fill_template():
    jj = _load_environment()
    if 'template' in request.args:
        template_name = request.args['template']
    else:
        return "ERROR: Template name not specified"

    vars = list(ct.show_template_variables(template_name))
    context = {}
    context['template'] = template_name
    context['variables'] = vars
    page_template = jj.get_template('enter_variables.j2')
    return page_template.render(context)

@app.route('/api/v1/push_template', methods=['POST'])
def push_template():
    context = dict(request.form)
    print(context)
    conductor_netconf_ip = context['conductor_netconf_ip']

    try:
        text_config = ct.get_text_config(context, context['template_name'])
        with open('consolidatedT128Model.xml') as t128_model:
            xml_config = ct.get_xml_config(text_config, t128_model)
    except ConfigParseError as e:
        return "There was an error in the config: {}".format(e)

    try:
        with t128ConfigHelper(host=conductor_netconf_ip) as ch:
            edit_status = ch.edit(xml_config, 'conductor timeout error')
    except RPCError as e:
        return "There was an error in the config: {}".format(e)

    if isinstance(edit_status, str):
        return edit_status

    if edit_status.ok:
        with t128ConfigHelper(host=conductor_netconf_ip) as ch:
            try:
                commit_status = ch.commit()
            except RPCError as e:
                return "There was an error committing the configuration, please check the candidate config: {}".format(e)
            if commit_status.ok:
                return "Configuration committed successfully"
            else:
                return "There was an error committing the config"
    else:
        return "There was an error adding the candidate config"

app.run(host='0.0.0.0')
