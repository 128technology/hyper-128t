from jinja2 import Environment, FileSystemLoader, meta

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


def get_template_variables(template_name):
    jinja = _load_config_template_environment()
    template_source = jinja.loader.get_source(jinja, template_name)[0]
    parsed_content = jinja.parse(template_source)
    return meta.find_undeclared_variables(parsed_content)


def get_template_string_variables(template):
    jinja = _load_config_template_environment()
    #template_source = jinja.loader.get_source(jinja, template_name)[0]
    parsed_content = jinja.parse(template)
    return meta.find_undeclared_variables(parsed_content)
