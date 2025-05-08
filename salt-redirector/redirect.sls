{%- set conductor = pillar.get('conductor') %}
{%- set preferences = '/root/redirect-preferences.json' %}

{%- if conductor %}
Create new initializer preferences file:
  file.managed:
    - name: {{ preferences }}
    - contents: |
        { "node-role": "combo", "node-name": "dummy-node", "router-name": "dummy-router", "conductor": {"primary": {"ip": "{{ conductor[0] }}"}{%- if conductor|length == 2 -%}, "secondary": {"ip": "{{ conductor[1] }}"}{%- endif -%}}}

Run initializer:
  cmd.run:
    - name: initialize128t -p {{ preferences }} --bypass-run-check
    - onchanges:
      - file: {{ preferences }}

Remove minion_master.pem:
  file.absent:
    - name: /etc/salt/pki/minion/minion_master.pub
    - onchanges:
      - file: {{ preferences }}

Restart salt-minion:
  service.running:
    - name: salt-minion
    - watch:
      - file: {{ preferences }}

Move initializer preferences file:
  file.rename:
    - source: {{ preferences }}
    - name: {{ preferences }}.old
    - force: True
{%- endif %}
