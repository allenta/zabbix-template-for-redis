#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
:url: https://github.com/allenta/zabbix-template-for-redis
:copyright: (c) 2016-2018 by Allenta Consulting S.L. <info@allenta.com>.
:license: BSD, see LICENSE.txt for more details.
'''

from __future__ import absolute_import
import json
import re
import subprocess
import sys
import time
from argparse import ArgumentParser

ITEMS = {
    'server': re.compile(
        r'^(?:'
        r'server:uptime_in_seconds|'
        r'clients:connected_clients|'
        r'clients:blocked_clients|'
        r'memory:used_memory|'
        r'memory:used_memory_rss|'
        r'memory:used_memory_lua|'
        r'memory:mem_fragmentation_ratio|'
        r'persistence:rdb_changes_since_last_save|'
        r'persistence:rdb_last_save_time|'
        r'persistence:rdb_last_bgsave_status|'
        r'persistence:rdb_last_bgsave_time_sec|'
        r'persistence:aof_last_rewrite_time_sec|'
        r'persistence:aof_last_bgrewrite_status|'
        r'persistence:aof_last_write_status|'
        r'stats:total_connections_received|'
        r'stats:total_commands_processed|'
        r'stats:total_net_input_bytes|'
        r'stats:total_net_output_bytes|'
        r'stats:rejected_connections|'
        r'stats:sync_full|'
        r'stats:sync_partial_ok|'
        r'stats:sync_partial_err|'
        r'stats:expired_keys|'
        r'stats:evicted_keys|'
        r'stats:keyspace_hits|'
        r'stats:keyspace_misses|'
        r'stats:pubsub_channels|'
        r'stats:pubsub_patterns|'
        r'replication:role|'
        r'replication:connected_slaves|'
        r'cpu:used_cpu_sys|'
        r'cpu:used_cpu_user|'
        r'cpu:used_cpu_sys_children|'
        r'cpu:used_cpu_user_children|'
        r'commandstats:[^:]+:(?:calls|usec_per_call)|'
        r'keyspace:[^:]+:(?:keys|expires|avg_ttl)|'
        r'cluster:cluster_state|'
        r'cluster:cluster_slots_assigned|'
        r'cluster:cluster_slots_ok|'
        r'cluster:cluster_slots_pfail|'
        r'cluster:cluster_slots_fail|'
        r'cluster:cluster_known_nodes|'
        r'cluster:cluster_size'
        r')$'),
    'sentinel': re.compile(
        r'^(?:'
        r'server:uptime_in_seconds|'
        r'sentinel:sentinel_masters|'
        r'sentinel:sentinel_running_scripts|'
        r'sentinel:sentinel_scripts_queue_length|'
        r'masters:[^:]+:(?:status|slaves|sentinels|ckquorum|usable_sentinels)|'
        r')$'),
}

SUBJECTS = {
    'server': {
        'items': None,
        'commandstats': re.compile(r'^commandstats:([^:]+):.+$'),
        'keyspace': re.compile(r'^keyspace:([^:]+):.+$'),
    },
    'sentinel': {
        'items': None,
        'masters': re.compile(r'^masters:([^:]+):.+$'),
    },
}


###############################################################################
## 'send' COMMAND
###############################################################################

def send(options):
    # Initializations.
    rows = ''
    now = int(time.time())

    # Build Zabbix sender input.
    for instance in options.redis_instances.split(','):
        instance = instance.strip()
        if instance:
            items = stats(instance, options.redis_type, options.redis_password)
            for name, value in items.items():
                row = '- redis_%(type)s.info["%(instance)s","%(key)s"] %(tst)d %(value)s\n' % {
                    'type': options.redis_type,
                    'instance': str2key(instance),
                    'key': str2key(name),
                    'tst': now,
                    'value': value,
                }
                sys.stdout.write(row)
                rows += row

    # Submit metrics.
    rc, output = execute('zabbix_sender -T -r -i - %(config)s %(server)s %(port)s %(host)s' % {
        'config':
            '-c "%s"' % options.zabbix_config
            if options.zabbix_config is not None else '',
        'server':
            '-z "%s"' % options.zabbix_server
            if options.zabbix_server is not None else '',
        'port':
            '-p %d' % options.zabbix_port
            if options.zabbix_port is not None else '',
        'host':
            '-s "%s"' % options.zabbix_host
            if options.zabbix_host is not None else '',
    }, stdin=rows)

    # Check return code.
    if rc == 0:
        sys.stdout.write(output)
    else:
        sys.stderr.write(output)
        sys.exit(1)


###############################################################################
## 'discover' COMMAND
###############################################################################

def discover(options):
    # Initializations.
    discovery = {
        'data': [],
    }

    # Build Zabbix discovery input.
    for instance in options.redis_instances.split(','):
        instance = instance.strip()
        if instance:
            if options.subject == 'items':
                discovery['data'].append({
                    '{#LOCATION}': instance,
                    '{#LOCATION_ID}': str2key(instance),
                })
            else:
                items = stats(instance, options.redis_type, options.redis_password)
                ids = set()
                for name in items.iterkeys():
                    match = SUBJECTS[options.redis_type][options.subject].match(name)
                    if match is not None and match.group(1) not in ids:
                        discovery['data'].append({
                            '{#LOCATION}': instance,
                            '{#LOCATION_ID}': str2key(instance),
                            '{#SUBJECT}': match.group(1),
                            '{#SUBJECT_ID}': str2key(match.group(1)),
                        })
                        ids.add(match.group(1))

    # Render output.
    sys.stdout.write(json.dumps(discovery, sort_keys=True, indent=2))


###############################################################################
## HELPERS
###############################################################################

def stats(location, type, password):
    # Initializations.
    result = {}
    clustered = False

    # Parse location of the Redis instance.
    prefix = 'unix://'
    if location.startswith(prefix):
        opts = '-s "%s"' % location[len(prefix):]
    else:
        if ':' in location:
            opts = '-h "%s" -p "%s"' % tuple(location.split(':', 1))
        else:
            opts = '-p "%s"' % location

    # Use password?
    if password is not None:
        opts += ' -a "%s"' % password

    # Fetch general stats through redis-cli.
    rc, output = execute('redis-cli %(opts)s INFO %(section)s' % {
        'opts': opts,
        'section': 'all' if type == 'server' else 'default',
    })
    if rc == 0:
        section = None
        for line in output.splitlines():
            if line.startswith('#'):
                section = line[1:].strip().lower()
            elif section is not None and ':' in line:
                key, value = (v.strip() for v in line.split(':', 1))
                if section == 'commandstats' and \
                   key.startswith('cmdstat_'):
                    key = key[8:].upper()
                name = '%s:%s' % (section, key)
                if ((type == 'server' and
                     section in ('keyspace', 'commandstats')) or \
                    (type == 'sentinel' and
                     section == 'sentinel' and
                     key.startswith('master'))):
                    subvalues = {}
                    for item in value.split(','):
                        if '=' in item:
                            subkey, subvalue = item.split('=', 1)
                            subvalues[subkey.strip()] = subvalue.strip()
                    for subkey, subvalue in subvalues.items():
                        subname = None
                        if type != 'sentinel':
                            subname = '%s:%s' % (name, subkey)
                        elif subkey != 'name' and 'name' in subvalues:
                            subname = 'masters:%s(%s):%s' % (
                                key, subvalues['name'], subkey)
                        elif subkey == 'name':
                            result.update(stats_sentinel(
                                opts,
                                subvalue,
                                'masters:%s(%s)' % (key, subvalue)))
                        if subname is not None:
                            if ITEMS[type].match(subname) is not None:
                                result[subname] = subvalue
                else:
                    if ITEMS[type].match(name) is not None:
                        result[name] = value
                    if name == 'cluster:cluster_enabled' and value == '1':
                        clustered = True
    else:
        sys.stderr.write(output)

    # Fetch cluster stats through redis-cli.
    if type == 'server' and clustered:
        result.update(stats_cluster(opts))

    # Done!
    return result


def stats_sentinel(opts, master_name, prefix):
    result = {}
    rc, output = execute('redis-cli %(opts)s SENTINEL ckquorum %(name)s' % {
        'opts': opts,
        'name': master_name,
    })
    if rc == 0:
        # Examples:
        #   - OK 3 usable Sentinels. Quorum and failover authorization can be reached
        #   - NOQUORUM 1 usable Sentinels. Not enough available Sentinels to reach the majority and authorize a failover
        name = '%s:ckquorum' % prefix
        if ITEMS['sentinel'].match(name) is not None:
            result[name] = '1' if output.startswith('OK') else '0'
        name = '%s:usable_sentinels' % prefix
        if ITEMS['sentinel'].match(name) is not None:
            items = output.split(' ', 2)
            if len(items) >= 2 and items[1].isdigit():
                result[name] = items[1]
    else:
        sys.stderr.write(output)
    return result


def stats_cluster(opts):
    result = {}
    rc, output = execute('redis-cli %(opts)s CLUSTER INFO' % {
        'opts': opts,
    })
    if rc == 0:
        for line in output.splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                name = 'cluster:%s' % key.strip()
                if ITEMS['server'].match(name) is not None:
                    result[name] = value.strip()
    else:
        sys.stderr.write(output)
    return result


def str2key(name):
    result = name
    for char in ['(', ')', ',']:
        result = result.replace(char, '\\' + char)
    return result


def execute(command, stdin=None):
    child = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True)
    output = child.communicate(input=stdin)[0]
    return child.returncode, output


###############################################################################
## MAIN
###############################################################################

def main():
    # Set up the base command line parser.
    parser = ArgumentParser()
    parser.add_argument(
        '-i', '--redis-instances', dest='redis_instances',
        type=str, required=True,
        help='comma-delimited list of Redis instances to get stats from '
             '(port, host:port and unix:///path/to/socket formats are alowed')
    parser.add_argument(
        '-t', '--redis-type', dest='redis_type',
        type=str, required=True, choices=SUBJECTS.keys(),
        help='the type of the Redis instance to get stats from')
    parser.add_argument(
        '--redis-password', dest='redis_password',
        type=str, default=None,
        help='password required to access to Redis instances')
    subparsers = parser.add_subparsers(dest='command')

    # Set up 'send' command.
    subparser = subparsers.add_parser(
        'send',
        help='submit stats through Zabbix sender')
    subparser.add_argument(
        '-c', '--zabbix-config', dest='zabbix_config',
        type=str, required=False, default=None,
        help='the Zabbix agent configuration file to fetch the configuration '
             'from')
    subparser.add_argument(
        '-z', '--zabbix-server', dest='zabbix_server',
        type=str, required=False, default=None,
        help='hostname or IP address of the Zabbix server / Zabbix proxy')
    subparser.add_argument(
        '-p', '--zabbix-port', dest='zabbix_port',
        type=int, required=False, default=None,
        help='port number of server trapper running on the Zabbix server / '
             'Zabbix proxy')
    subparser.add_argument(
        '-s', '--zabbix-host', dest='zabbix_host',
        type=str, required=False, default=None,
        help='host name as registered in the Zabbix frontend')

    # Set up 'discover' command.
    subparser = subparsers.add_parser(
        'discover',
        help='generate Zabbix discovery schema')
    subparser.add_argument(
        'subject', type=str,
        help='dynamic resources to be discovered')

    # Parse command line arguments.
    options = parser.parse_args()

    # Check required arguments.
    if options.command == 'send':
        if options.zabbix_config is None and options.zabbix_server is None:
            parser.print_help()
            sys.exit(1)

    # Check subject to be discovered.
    if options.command == 'discover':
        subjects = SUBJECTS[options.redis_type].keys()
        if options.subject not in subjects:
            sys.stderr.write('Invalid subject (choose from %(subjects)s)\n' % {
                'subjects': ', '.join("'{0}'".format(s) for s in subjects),
            })
            sys.exit(1)

    # Execute command.
    globals()[options.command](options)
    sys.exit(0)

if __name__ == '__main__':
    main()
