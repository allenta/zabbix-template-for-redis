**This is a Zabbix template + discovery & sender script useful to monitor Redis Server & Redis Sentinel instances:**

1. Copy ``zabbix-redis.py`` to ``/usr/local/bin/``.

2. Add the ``redis_server.discovery`` and / or ``redis_sentinel.discovery`` user parameters to Zabbix::

    UserParameter=redis_server.discovery[*],/usr/local/bin/zabbix-redis.py -i '$1' -t server discover $2 2> /dev/null
    UserParameter=redis_sentinel.discovery[*],/usr/local/bin/zabbix-redis.py -i '$1' -t sentinel discover $2 2> /dev/null

3. Add required jobs to the ``zabbix`` user crontab (beware of the ``-i``, ``-t`` and ``-s`` options). This will submit Redis Server and / or Redis Sentinel metrics through Zabbix Sender::

    * * * * * /usr/local/bin/zabbix-redis.py -i '6379, 6380, 6381, 7000, 7001, 7002, 7003, 7004, 7005' -t server send -c /etc/zabbix/zabbix_agentd.conf -s dev > /dev/null 2>&1
    * * * * * /usr/local/bin/zabbix-redis.py -i '26379, 26380, 26381' -t sentinel send -c /etc/zabbix/zabbix_agentd.conf -s dev > /dev/null 2>&1

4. Import the required templates (``template-app-redis-server.xml`` and / or ``template-app-redis-sentinel.xml`` files).

5. Add an existing / new host to the ``Redis servers`` group and link it to the right template (``Template App Redis Server`` for Redis Server and ``Template App Redis Sentinel`` for Redis Sentinel). Beware depending on the used template you must set a value for the ``{$REDIS_SERVER_LOCATIONS}`` or ``{$REDIS_SENTINEL_LOCATIONS}`` macro (comma-delimited list of Redis instances; ``port``, ``host:port`` and ``unix:///path/to/socket`` formats are allowed).

6. Adjust triggers and trigger prototypes according with your preferences.
