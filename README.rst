**This is a Zabbix template + script useful to monitor Redis Server & Redis Sentinel instances:**

1. Copy ``zabbix-redis.py`` to ``/usr/local/bin/``.

2. Add the ``redis_server.discovery`` & ``redis_server.stats`` and / or ``redis_sentinel.discovery`` & ``redis_sentinel.stats`` user parameters to Zabbix::

    UserParameter=redis_server.discovery[*],/usr/local/bin/zabbix-redis.py -i '$1' -t server discover $2 2> /dev/null
    UserParameter=redis_server.stats[*],/usr/local/bin/zabbix-redis.py -i '$1' -t server stats 2> /dev/null
    UserParameter=redis_sentinel.discovery[*],/usr/local/bin/zabbix-redis.py -i '$1' -t sentinel discover $2 2> /dev/null
    UserParameter=redis_sentinel.stats[*],/usr/local/bin/zabbix-redis.py -i '$1' -t sentinel stats 2> /dev/null

3. Import the templates. You may download the appropriate versions from `the releases page <https://github.com/allenta/zabbix-template-for-redis/releases/latest/>`_ or generate them using the Jinja2 skeletons::

    $ pip install jinja2-cli
    $ PYTHONPATH=. jinja2 \
        -D version={5.0,5.2,5.4,6.0,6.2} \
        [-D name='Redis Server'] \
        [-D description=''] \
        --extension=extensions.zabbix.ZabbixExtension --strict -o template.xml template-app-redis-server.j2
    $ PYTHONPATH=. jinja2 \
        -D version={5.0,5.2,5.4,6.0,6.2} \
        [-D name='Redis Sentinel'] \
        [-D description=''] \
        --extension=extensions.zabbix.ZabbixExtension --strict -o template.xml template-app-redis-sentinel.j2

4. Link hosts to the templates. Beware depending on the used template you must set a value for the ``{$REDIS_SERVER.LOCATIONS}`` or ``{$REDIS_SENTINEL.LOCATIONS}`` macro (comma-delimited list of Redis instances; ``port``, ``host:port`` and ``unix:///path/to/socket`` formats are allowed). Additional macros and contexts are available for further customizations.
