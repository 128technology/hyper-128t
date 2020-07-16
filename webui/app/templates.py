from jinja2 import Environment, FileSystemLoader, meta, Template
import os

TEMPLATE_DIR = 'config_templates'


def _filter_out_test_templates(template_name):
    if template_name.startswith('test-'):
        return False
    return True


def _load_config_template_environment():
    return Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def get_config_templates():
    jinja = _load_config_template_environment()
    return jinja.list_templates(filter_func=_filter_out_test_templates)


def filter_template_vars(template_vars):
    exclude_keys = [
        'conductor_ips',
        '_deployment_name_',
        '_deployment_short_name_',
        '_site_name_',
    ]
    for key in exclude_keys:
        if key in template_vars:
            template_vars.remove(key)


def get_template_variables(template_name):
    jinja = _load_config_template_environment()
    template_source = jinja.loader.get_source(jinja, template_name)[0]
    parsed_content = jinja.parse(template_source)
    template_vars = meta.find_undeclared_variables(parsed_content)
    filter_template_vars(template_vars)
    return template_vars


def get_template_string_variables(template):
    jinja = _load_config_template_environment()
    #template_source = jinja.loader.get_source(jinja, template_name)[0]
    parsed_content = jinja.parse(template)
    template_vars = meta.find_undeclared_variables(parsed_content)
    filter_template_vars(template_vars)
    return template_vars


def get_template_content(file_name):
    with open(os.path.join(TEMPLATE_DIR, file_name)) as fd:
        content = fd.read()
        return content
    return ''


def get_rendered_template(template_string, parameters):
    template = Template(template_string)
    return template.render(parameters)
