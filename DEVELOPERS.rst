General tips
============

- Templates:
    1. ``http://192.168.100.173/zabbix``
        - Default username/password is ``admin``/``zabbix``.

    2. In 'Configuration > Templates' click on 'Import' and select ``template-app-redis-server.xml``.

    2. In 'Configuration > Templates' click on 'Import' and select ``template-app-redis-sentinel.xml``.

    3. In 'Configuration > Hosts' click on 'Create host':
        - Host name: ``dev``
        - Group: ``Redis servers``
        - Linked templates: ``Template App Redis Server`` and / or ``Template App Redis Sentinel``
