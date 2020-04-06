from ncclient import manager
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport.errors import TransportError

from lxml import etree

# We'll use this to interact with Netconf
class ncclientAgent(object):

    def __init__(self, ncclient_manager):
        self.netconf_session = ncclient_manager

    def editConfig(self, target_config, config_xml):
        #edit_status = self.netconf_session.edit_config(target=target_config, config=etree.tostring(config_xml, encoding='unicode'), format='text')
        edit_status = self.netconf_session.edit_config(target=target_config, config=config_xml)
        return edit_status

    def replaceConfig(self, target_config, config_xml):
        replace_status = self.netconf_session.edit_config(target=target_config, config=config_xml, default_operation="replace")
        return replace_status

    def removeConfig(self, target_config, config_xml):
        remove_status = self.netconf_session.delete_config(source=config_xml, target=target_config)
        return remove_status

    def commitConfig(self, validationType='distributed'):
        if validationType == 'distributed':
          commit_status = self.netconf_session.commit()
        else:
          commit_command = etree.Element('{urn:ietf:params:xml:ns:netconf:base:1.0}commit', {'nc':'urn:ietf:params:xml:ns:netconf:base:1.0'})
          vt = etree.Element('{urn:128technology:netconf:validate-type:1.0}validation-type', {'vt':'urn:128technology:netconf:validate-type:1.0'})
          vt.text = validationType
          commit_command.append(vt)
          commit_status = self.netconf_session.dispatch(commit_command)
        self.netconf_session.close_session()
        return commit_status

# We can simplify the 128T actions to push config and commit
class t128Configurator(object):

    def __init__(self, config_agent):
        self.config_agent = config_agent

    def config(self, candidate_config_xml, state):
        action_status = "None"
        if state == "edit":
            action_status = self.config_agent.editConfig("candidate", candidate_config_xml)
        if state == "replace":
            action_status = self.config_agent.replaceConfig("candidate", candidate_config_xml)

        return action_status

    def commit(self, validationType='distributed'):
        commit_status = self.config_agent.commitConfig(validationType=validationType)
        return commit_status

class t128ConfigHelper(object):

    def __init__(self, host='127.0.0.1', port='830', username='admin', key_filename='/home/admin/.ssh/pdc_ssh_key'):
        self.netconf_session = manager.connect(
            host=host,
            port=port,
            username=username,
            key_filename=key_filename,
            allow_agent=True,
            look_for_keys=False,
            hostkey_verify=False,
            timeout=1200
        )
        ncclient_agent = ncclientAgent(self.netconf_session)
        self.t128_configurator = t128Configurator(ncclient_agent)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            self.netconf_session.close_session()
        except TransportError:
            #print("we had a transport error for whatever reason")
            pass

    def edit(self, config_xml, err_msg):
        try:
            return self.t128_configurator.config(config_xml, 'edit')
        except TimeoutExpiredError:
            return err_msg

    def commit(self):
        try:
            return self.t128_configurator.commit()
        except TimeoutExpiredError:
            return "Error: timeout on Netconf API"
