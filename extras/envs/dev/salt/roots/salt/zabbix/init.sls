zabbix.repository:
  pkg.installed:
    - sources:
      - zabbix-release: http://repo.zabbix.com/zabbix/2.4/ubuntu/pool/main/z/zabbix-release/zabbix-release_2.4-1+trusty_all.deb

zabbix.packages:
  pkg.installed:
    - refresh: True
    - pkgs:
      - zabbix-agent
      - zabbix-frontend-php
      - zabbix-sender
      - zabbix-server-mysql
    - requires:
      - pkg: zabbix.repository

zabbix.zabbix-server-service:
  service.running:
    - name: zabbix-server
    - require:
      - pkg: zabbix.packages
      - sls: redis

zabbix.zabbix-agent-service:
  service.running:
    - name: zabbix-agent
    - require:
      - pkg: zabbix.packages
      - sls: redis

zabbix.mysql-service:
  service.running:
    - name: mysql
    - require:
      - pkg: zabbix.packages
      - sls: redis

zabbix.apache2-service:
  service.running:
    - name: apache2
    - require:
      - pkg: zabbix.packages
      - sls: redis

/etc/apache2/conf-available/zabbix.conf:
  file.replace:
    - pattern: '^\s*#?\s*php_value\s*date\.timezone\s*.*'
    - repl: '    php_value date.timezone Europe/Madrid'
    - watch_in:
      - service: zabbix.apache2-service
    - require:
      - pkg: zabbix.packages
      - sls: redis

/etc/zabbix/web/zabbix.conf.php:
  file.managed:
    - source: salt://zabbix/zabbix.conf.php.tmpl
    - template: jinja
    - defaults:
      db_name: {{ pillar['mysql.zabbix']['name'] }}
      db_user: {{ pillar['mysql.zabbix']['user'] }}
      db_password: {{ pillar['mysql.zabbix']['password'] }}
    - user: www-data
    - group: www-data
    - mode: 644
    - watch_in:
      - service: zabbix.apache2-service
    - require:
      - pkg: zabbix.packages
      - sls: redis

{% for name, value in [('DBHost', '127.0.0.1'),
                       ('DBName', pillar['mysql.zabbix']['name']),
                       ('DBUser', pillar['mysql.zabbix']['user']),
                       ('DBPassword', pillar['mysql.zabbix']['password']),] %}
/etc/zabbix/zabbix_server.conf-{{ loop.index }}:
  file.replace:
    - name: /etc/zabbix/zabbix_server.conf
    - pattern: '^\s*#?\s*{{ name }}\s*=\s*.*'
    - repl: {{name}}={{value}}
    - append_if_not_found: True
    - watch_in:
      - service: zabbix.zabbix-server-service
    - require:
      - pkg: zabbix.packages
      - sls: redis
{% endfor %}

{% for name, value in [('UserParameter', "redis_server.discovery[*],/vagrant/zabbix-redis.py -i '$1' -t server discover $2 2> /dev/null"),
                       ('UserParameter', "redis_sentinel.discovery[*],/vagrant/zabbix-redis.py -i '$1' -t sentinel discover $2 2> /dev/null"),
                       ('Hostname', 'dev')] %}
/etc/zabbix/zabbix_agentd.conf-{{ loop.index }}:
  file.append:
    - name: /etc/zabbix/zabbix_agentd.conf
    - text: {{name}}={{value}}
    - watch_in:
      - service: zabbix.zabbix-agent-service
    - require:
      - pkg: zabbix.packages
      - sls: redis
{% endfor %}

zabbix.mysql-set-root-password:
  cmd.run:
    - user: vagrant
    - unless: mysqladmin -uroot -p{{ pillar['mysql.root']['password'] }} status
    - name: mysqladmin -uroot password {{ pillar['mysql.root']['password'] }}
    - require:
      - service: zabbix.mysql-service

zabbix.mysql-create-db:
  mysql_database.present:
    - name: {{ pillar['mysql.zabbix']['name'] }}
    - connection_user: root
    - connection_pass: {{ pillar['mysql.root']['password'] }}
    - connection_charset: utf8
    - require:
      - cmd: zabbix.mysql-set-root-password
  mysql_user.present:
    - name: {{ pillar['mysql.zabbix']['user'] }}
    - host: localhost
    - password: {{ pillar['mysql.zabbix']['password'] }}
    - connection_user: root
    - connection_pass: {{ pillar['mysql.root']['password'] }}
    - connection_charset: utf8
    - require:
      - mysql_database: zabbix.mysql-create-db
  mysql_grants.present:
    - grant: all privileges
    - database: {{ pillar['mysql.zabbix']['name'] }}.*
    - user: {{ pillar['mysql.zabbix']['user'] }}
    - host: localhost
    - connection_user: root
    - connection_pass: {{ pillar['mysql.root']['password'] }}
    - connection_charset: utf8
    - require:
      - mysql_user: zabbix.mysql-create-db
