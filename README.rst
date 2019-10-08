**This is a Zabbix template + discovery & sender script useful to monitor Redis Server & Redis Sentinel instances:**

1. Copy ``zabbix-redis.py`` to ``/usr/local/bin/``.

2. Add the ``redis_server.discovery`` & ``redis_server.stats`` and / or ``redis_sentinel.discovery`` & ``redis_sentinel.stats`` user parameters to Zabbix::

    UserParameter=redis_server.discovery[*],/usr/local/bin/zabbix-redis.py -i '$1' -t server discover $2 2> /dev/null
    UserParameter=redis_server.stats[*],/usr/local/bin/zabbix-redis.py -i '$1' -t server stats 2> /dev/null
    UserParameter=redis_sentinel.discovery[*],/usr/local/bin/zabbix-redis.py -i '$1' -t sentinel discover $2 2> /dev/null
    UserParameter=redis_sentinel.stats[*],/usr/local/bin/zabbix-redis.py -i '$1' -t sentinel stats 2> /dev/null

3. Generate the required templates using the Jinja2 skeleton and import them::

    $ pip install jinja2-cli
    $ jinja2 --strict -D version='{4.0,4.2}' -o template.xml template-app-redis-server.j2
    $ jinja2 --strict -D version='{4.0,4.2}' -o template.xml template-app-redis-sentinel.j2

4. Add an existing / new host to the ``Redis servers`` group and link it to the right template (``Template App Redis Server`` for Redis Server and ``Template App Redis Sentinel`` for Redis Sentinel). Beware depending on the used template you must set a value for the ``{$REDIS_SERVER.LOCATIONS}`` or ``{$REDIS_SENTINEL.LOCATIONS}`` macro (comma-delimited list of Redis instances; ``port``, ``host:port`` and ``unix:///path/to/socket`` formats are allowed). Additional macros contexts are available for further customizations.
