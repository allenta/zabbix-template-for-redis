General tips
============

- Templates:
    1. ``http://192.168.100.173/zabbix``
        - Default username/password is ``Admin``/``zabbix``.

    2. In 'Configuration > Templates' click on 'Import' and select ``template-app-redis-server.xml``.

    2. In 'Configuration > Templates' click on 'Import' and select ``template-app-redis-sentinel.xml``.

    3. In 'Configuration > Hosts' click on 'Create host':
        - Host name: ``dev``
        - Group: ``Redis servers``
        - Linked templates: ``Template App Redis Server`` and / or ``Template App Redis Sentinel``
        - Macros: ``{$REDIS_SERVER.LOCATIONS}`` => ``6379, 6380, 6381, 7000, 7001, 7002, 7003, 7004, 7005`` and/or ``{$REDIS_SENTINEL.LOCATIONS}`` => ``26379, 26380, 26381``
