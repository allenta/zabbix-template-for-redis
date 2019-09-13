**This is a Zabbix template + discovery & sender script useful to monitor Redis Server & Redis Sentinel instances:**

1. Copy ``zabbix-redis.py`` to ``/usr/local/bin/``.

2. Add the ``redis_server.discovery`` & ``redis_server.stats`` and / or ``redis_sentinel.discovery`` & ``redis_sentinel.stats`` user parameters to Zabbix::

    UserParameter=redis_server.discovery[*],/usr/local/bin/zabbix-redis.py -i '$1' -t server discover $2 2> /dev/null
    UserParameter=redis_server.stats[*],/usr/local/bin/zabbix-redis.py -i '$1' -t server stats 2> /dev/null
    UserParameter=redis_sentinel.discovery[*],/usr/local/bin/zabbix-redis.py -i '$1' -t sentinel discover $2 2> /dev/null
    UserParameter=redis_sentinel.stats[*],/usr/local/bin/zabbix-redis.py -i '$1' -t sentinel stats 2> /dev/null

3. Import the required templates (``template-app-redis-server.xml`` and / or ``template-app-redis-sentinel.xml`` files).

4. Add an existing / new host to the ``Redis servers`` group and link it to the right template (``Template App Redis Server`` for Redis Server and ``Template App Redis Sentinel`` for Redis Sentinel). Beware depending on the used template you must set a value for the ``{$REDIS_SERVER.LOCATIONS}`` or ``{$REDIS_SENTINEL.LOCATIONS}`` macro (comma-delimited list of Redis instances; ``port``, ``host:port`` and ``unix:///path/to/socket`` formats are allowed). There are defined macros for ``Template App Redis Server`` and ``Template App Redis Sentinel``.

   For ``Template App Redis Server``:

   * ``{$REDIS_SERVER.EVICTED_KEYS.MAX}``
   * ``{$REDIS_SERVER.ITEM_HISTORY_STORAGE_PERIOD}``
   * ``{$REDIS_SERVER.ITEM_TREND_STORAGE_PERIOD}``
   * ``{$REDIS_SERVER.ITEM_UPDATE_INTERVAL}``
   * ``{$REDIS_SERVER.LAST_VALUES_TO_CHECK}``
   * ``{$REDIS_SERVER.LLD_KEEP_LOST_RESOURCES_PERIOD}``
   * ``{$REDIS_SERVER.LLD_UPDATE_INTERVAL}``
   * ``{$REDIS_SERVER.LOCATIONS}``
   * ``{$REDIS_SERVER.PROCESSES.MIN}``
   * ``{$REDIS_SERVER.UPTIME.MIN}``

   For ``Template App Redis Sentinel``:

   * ``{$REDIS_SENTINEL.ITEM_HISTORY_STORAGE_PERIOD}``
   * ``{$REDIS_SENTINEL.ITEM_TREND_STORAGE_PERIOD}``
   * ``{$REDIS_SENTINEL.ITEM_UPDATE_INTERVAL}``
   * ``{$REDIS_SENTINEL.LAST_VALUES_TO_CHECK}``
   * ``{$REDIS_SENTINEL.LLD_KEEP_LOST_RESOURCES_PERIOD}``
   * ``{$REDIS_SENTINEL.LLD_UPDATE_INTERVAL}``
   * ``{$REDIS_SENTINEL.LOCATIONS}``
   * ``{$REDIS_SENTINEL.PROCESSES.MIN}``
   * ``{$REDIS_SENTINEL.UPTIME.MIN}``

   It's also possible to use **contexts** on macros, for example:

   * ``{$REDIS_SERVER.ITEM_HISTORY_STORAGE_PERIOD:items:cluster-cluster_slots_assigned}``
   * ``{$REDIS_SENTINEL.ITEM_HISTORY_STORAGE_PERIOD:items:server-uptime_in_seconds}``

5. Adjust triggers and trigger prototypes according with your preferences.
