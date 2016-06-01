user.color-prompt:
  file.replace:
    - name: /home/vagrant/.bashrc
    - pattern: '#force_color_prompt=yes'
    - repl: 'force_color_prompt=yes'

user.zabbix-sender-server-cron:
  cron.present:
    - user: zabbix
    - name: PATH=$PATH:/usr/local/bin /vagrant/zabbix-redis.py -i '6379, 6380, 6381, 7000, 7001, 7002, 7003, 7004, 7005' -t server send -c /etc/zabbix/zabbix_agentd.conf -s dev > /dev/null 2>&1
    - require:
      - sls: zabbix

user.zabbix-sender-sentinel-cron:
  cron.present:
    - user: zabbix
    - name: PATH=$PATH:/usr/local/bin /vagrant/zabbix-redis.py -i '26379, 26380, 26381' -t sentinel send -c /etc/zabbix/zabbix_agentd.conf -s dev > /dev/null 2>&1
    - require:
      - sls: zabbix
