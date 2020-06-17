{%- set conductor = pillar.get('conductor') %}
{%- if conductor %}
Fix Salt master:
  file.replace:
  - name: /etc/salt/minion
    pattern: |
      master:
      (\s*- .*$){1,2}
    repl: |
      master:
{%- for ip in conductor %}
      - {{ ip }}
{%- endfor %}

Remove minion_master.pem:
  file.absent:
    - name: /etc/salt/pki/minion/minion_master.pub
    - onchanges:
      - file: /etc/salt/minion

Restart salt-minion:
  service.running:
    - name: salt-minion
    - watch:
      - file: /etc/salt/minion
{%- endif %}
