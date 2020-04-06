from lib.ote_utils.utils import Config
from jinja2 import Environment, FileSystemLoader, meta
from jinja2.exceptions import TemplateNotFound
import os

TEMPLATE_DIR = 'config_templates'

def _load_config_template_environment():
  return Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def _create_config(context, template_file):
  JINJA = _load_config_template_environment()
  try:
    template = JINJA.get_template(template_file)
  except (TemplateNotFound, KeyError):
    return ''
  return template.render(context)

def _filter_out_test_templates(template_name):
  if template_name.startswith('test-'):
    return False
  return True

def list_config_templates():
  JINJA = _load_config_template_environment()
  return JINJA.list_templates(filter_func=_filter_out_test_templates)

def show_template_variables(template_name):
  JINJA = _load_config_template_environment()
  template_source = JINJA.loader.get_source(JINJA, template_name)[0]
  parsed_content = JINJA.parse(template_source)
  return meta.find_undeclared_variables(parsed_content)

def _convert_config_to_xml(text_config, model):
  cc = Config.Config()
  cc.load_t128_config_model(model)
  config_xml = cc.convert_config_to_netconf_xml(text_config.split('\n'))
  return config_xml

def get_text_config(context, template_file):
  config_text = _create_config(context, template_file)
  return config_text

def get_xml_config(config_text, model='/var/model/consolidatedT128Model.xml'):
  config_xml = _convert_config_to_xml(config_text, model)
  return config_xml
