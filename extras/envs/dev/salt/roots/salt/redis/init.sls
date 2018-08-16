{% set version = '3.0.7' %}
{% set standalone_ports = [6379, 6380, 6381] %}
{% set sentinel_ports = [26379, 26380, 26381] %}
{% set cluster_ports = [7000, 7001, 7002, 7003, 7004, 7005] %}

redis.gem:
  gem.installed:
    - user: root
    - name: redis
    - version: 3.3.0
    - require:
      - sls: global

redis.download-and-install:
  cmd.run:
    - runas: vagrant
    - creates: /home/vagrant/.vagrant.redis.download-and-install
    - name: |
        set -e

        cd /home/vagrant
        wget http://download.redis.io/releases/redis-{{ version }}.tar.gz
        tar zxvf redis-*.tar.gz
        rm -f redis-*.tar.gz
        cd redis-*
        make
        sudo make PREFIX="/usr/local" install
        sudo ldconfig
        sudo cp src/redis-trib.rb /usr/local/bin

        touch /home/vagrant/.vagrant.redis.download-and-install
    - require:
      - sls: global

redis.create-instances:
  cmd.run:
    - runas: root
    - creates: /home/vagrant/.vagrant.redis.create-instances
    - name: |
        set -e

        mkdir -p /etc/redis /var/lib/redis

        for PORT in {{ standalone_ports|join(' ') }} {{ cluster_ports|join(' ') }}; do
          cp /home/vagrant/redis*/utils/redis_init_script /etc/init.d/redis-server-$PORT
          sed /etc/init.d/redis-server-$PORT -i \
            -e "s%^REDISPORT=.*%REDISPORT=$PORT%" \
            -e "s%^PIDFILE=/var/run/redis_%PIDFILE=/var/run/redis-%"
          chmod +x /etc/init.d/redis-server-$PORT
          update-rc.d -f redis-server-$PORT defaults

          cp /home/vagrant/redis*/redis.conf /etc/redis/$PORT.conf
          sed /etc/redis/$PORT.conf -i \
            -e "s%^port .*%port $PORT%" \
            -e "s%^dir .*%dir /var/lib/redis%" \
            -e "s%^daemonize .*%daemonize yes%" \
            -e "s%^pidfile .*%pidfile /var/run/redis-$PORT.pid%" \
            -e "s%^dbfilename .*%dbfilename dump-$PORT.rdb%" \
            -e "s%^appendfilename .*%appendfilename appendonly-$PORT.aof%" \
            -e "s%^logfile .*%logfile /var/log/redis-$PORT.log%"
        done

        touch /home/vagrant/.vagrant.redis.create-instances
    - require:
      - cmd: redis.download-and-install

redis.set-up-standalone-instances:
  cmd.run:
    - runas: root
    - creates: /home/vagrant/.vagrant.redis.set-up-standalone-instances
    - name: |
        set -e

        service redis-server-{{ standalone_ports[0] }} start
        for PORT in {{ standalone_ports[1:]|join(' ') }}; do
          sed /etc/redis/$PORT.conf -i \
            -e "s%^# slaveof .*%slaveof 127.0.0.1 {{ standalone_ports[0] }}%"
          service redis-server-$PORT start
        done

        for PORT in {{ sentinel_ports|join(' ') }}; do
          cp /home/vagrant/redis*/utils/redis_init_script /etc/init.d/redis-sentinel-$PORT
          sed /etc/init.d/redis-sentinel-$PORT -i \
            -e "s%^\(EXEC=.*\)/redis-server%\1/redis-sentinel%" \
            -e "s%^REDISPORT=.*%REDISPORT=$PORT%" \
            -e "s%^PIDFILE=/var/run/redis_%PIDFILE=/var/run/redis-%"
          chmod +x /etc/init.d/redis-sentinel-$PORT
          update-rc.d -f redis-sentinel-$PORT defaults

          echo "port $PORT" > /etc/redis/$PORT.conf
          echo "dir /var/lib/redis" >> /etc/redis/$PORT.conf
          echo "daemonize yes" >> /etc/redis/$PORT.conf
          echo "pidfile /var/run/redis-$PORT.pid" >> /etc/redis/$PORT.conf
          echo "logfile /var/log/redis-$PORT.log" >> /etc/redis/$PORT.conf
          echo "sentinel monitor mymaster 127.0.0.1 {{ standalone_ports[0] }} 1" >> /etc/redis/$PORT.conf
          echo "sentinel down-after-milliseconds mymaster 5000" >> /etc/redis/$PORT.conf
          echo "sentinel failover-timeout mymaster 60000" >> /etc/redis/$PORT.conf
          echo "sentinel parallel-syncs mymaster 1" >> /etc/redis/$PORT.conf

          service redis-sentinel-$PORT start
        done

        touch /home/vagrant/.vagrant.redis.set-up-standalone-instances
    - require:
      - cmd: redis.create-instances

redis.set-up-clustered-instances:
  cmd.run:
    - runas: root
    - creates: /home/vagrant/.vagrant.redis.set-up-clustered-instances
    - name: |
        set -e

        for PORT in {{ cluster_ports|join(' ') }}; do
          sed /etc/redis/$PORT.conf -i \
            -e "s%^# cluster-enabled .*%cluster-enabled yes%" \
            -e "s%^# cluster-config-file .*%cluster-config-file nodes-$PORT.conf%" \
            -e "s%^# cluster-node-timeout .*%cluster-node-timeout 5000%" \
            -e "s%^# appendonly .*%appendonly yes%"
          service redis-server-$PORT start
        done

        yes yes | redis-trib.rb create --replicas 1 \
{%- for port in cluster_ports %}
          127.0.0.1:{{ port }} \
{%- endfor %}
        && touch /home/vagrant/.vagrant.redis.set-up-clustered-instances
    - require:
      - cmd: redis.create-instances
