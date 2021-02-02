#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
:url: https://github.com/allenta/zabbix-template-for-redis
:copyright: (c) 2016-2021 by Allenta Consulting S.L. <info@allenta.com>.
:license: BSD, see LICENSE.txt for more details.
'''

from __future__ import absolute_import, division, print_function, unicode_literals
import json
import re
import subprocess
import sys
from argparse import ArgumentParser

TYPE_COUNTER = 1
TYPE_GAUGE = 2
TYPE_OTHER = 3
TYPES = (TYPE_COUNTER, TYPE_GAUGE, TYPE_OTHER)

ITEMS = {
    'server': (
        (r'server:uptime_in_seconds', TYPE_GAUGE),
        (r'clients:connected_clients', TYPE_GAUGE),
        (r'clients:blocked_clients', TYPE_GAUGE),
        (r'memory:used_memory', TYPE_GAUGE),
        (r'memory:used_memory_rss', TYPE_GAUGE),
        (r'memory:used_memory_lua', TYPE_GAUGE),
        (r'memory:mem_fragmentation_ratio', TYPE_GAUGE),
        (r'persistence:rdb_changes_since_last_save', TYPE_GAUGE),
        (r'persistence:rdb_last_save_time', TYPE_GAUGE),
        (r'persistence:rdb_last_bgsave_status', TYPE_OTHER),
        (r'persistence:rdb_last_bgsave_time_sec', TYPE_GAUGE),
        (r'persistence:aof_last_rewrite_time_sec', TYPE_GAUGE),
        (r'persistence:aof_last_bgrewrite_status', TYPE_OTHER),
        (r'persistence:aof_last_write_status', TYPE_OTHER),
        (r'stats:total_connections_received', TYPE_COUNTER),
        (r'stats:total_commands_processed', TYPE_COUNTER),
        (r'stats:total_net_input_bytes', TYPE_COUNTER),
        (r'stats:total_net_output_bytes', TYPE_COUNTER),
        (r'stats:rejected_connections', TYPE_COUNTER),
        (r'stats:sync_full', TYPE_COUNTER),
        (r'stats:sync_partial_ok', TYPE_COUNTER),
        (r'stats:sync_partial_err', TYPE_COUNTER),
        (r'stats:expired_keys', TYPE_COUNTER),
        (r'stats:evicted_keys', TYPE_COUNTER),
        (r'stats:keyspace_hits', TYPE_COUNTER),
        (r'stats:keyspace_misses', TYPE_COUNTER),
        (r'stats:pubsub_channels', TYPE_GAUGE),
        (r'stats:pubsub_patterns', TYPE_GAUGE),
        (r'replication:role', TYPE_GAUGE),
        (r'replication:connected_slaves', TYPE_GAUGE),
        (r'cpu:used_cpu_sys', TYPE_COUNTER),
        (r'cpu:used_cpu_user', TYPE_COUNTER),
        (r'cpu:used_cpu_sys_children', TYPE_COUNTER),
        (r'cpu:used_cpu_user_children', TYPE_COUNTER),
        (r'commandstats:[^:]+:calls', TYPE_COUNTER),
        (r'commandstats:[^:]+:usec_per_call', TYPE_GAUGE),
        (r'keyspace:[^:]+:(?:keys|expires|avg_ttl)', TYPE_GAUGE),
        (r'cluster:cluster_state', TYPE_GAUGE),
        (r'cluster:cluster_slots_assigned', TYPE_GAUGE),
        (r'cluster:cluster_slots_ok', TYPE_GAUGE),
        (r'cluster:cluster_slots_pfail', TYPE_GAUGE),
        (r'cluster:cluster_slots_fail', TYPE_GAUGE),
        (r'cluster:cluster_known_nodes', TYPE_GAUGE),
        (r'cluster:cluster_size', TYPE_GAUGE),
    ),
    'sentinel': (
        (r'server:uptime_in_seconds', TYPE_GAUGE),
        (r'sentinel:sentinel_masters', TYPE_GAUGE),
        (r'sentinel:sentinel_running_scripts', TYPE_GAUGE),
        (r'sentinel:sentinel_scripts_queue_length', TYPE_GAUGE),
        (r'masters:[^:]+:(?:status|slaves|sentinels|ckquorum|usable_sentinels)', TYPE_GAUGE),
    ),
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
## 'stats' COMMAND
###############################################################################

def stats(options):
    # Initializations.
    result = {}

    # Build master item contents.
    for instance in options.redis_instances.split(','):
        instance = instance.strip()
        stats = _stats(
            instance,
            options.redis_type,
            options.redis_user,
            options.redis_password)
        for item in stats.items:
            result['%(instance)s.%(name)s' % {
                'instance': _safe_zabbix_string(instance),
                'name': _safe_zabbix_string(item.name),
            }] = item.value

    # Render output.
    sys.stdout.write(json.dumps(result, separators=(',', ':')))


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
        if options.subject == 'items':
            discovery['data'].append({
                '{#LOCATION}': instance,
                '{#LOCATION_ID}': _safe_zabbix_string(instance),
            })
        else:
            stats = _stats(
                instance,
                options.redis_type,
                options.redis_user,
                options.redis_password)
            for subject in stats.subjects(options.subject):
                discovery['data'].append({
                    '{#LOCATION}': instance,
                    '{#LOCATION_ID}': _safe_zabbix_string(instance),
                    '{#SUBJECT}': subject,
                    '{#SUBJECT_ID}': _safe_zabbix_string(subject),
                })

    # Render output.
    sys.stdout.write(json.dumps(discovery, sort_keys=True, indent=2))


###############################################################################
## HELPERS
###############################################################################

class Item(object):
    '''
    A class to hold all relevant information about an item in the stats: name,
    value, type and subject (type & value).
    '''

    def __init__(
            self, name, value, type, subject_type=None, subject_value=None):
        # Set name and value.
        self._name = name
        self._value = value
        self._type = type
        self._subject_type = subject_type or 'items'
        self._subject_value = subject_value

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def type(self):
        return self._type

    @property
    def subject_type(self):
        return self._subject_type

    @property
    def subject_value(self):
        return self._subject_value

    def aggregate(self, value):
        # Aggregate another value. Only counter and gauges can be aggregated.
        # In any other case, mark this item's value as discarded.
        if self.type in (TYPE_COUNTER, TYPE_GAUGE):
            self._value += value
        else:
            self._value = None


class Stats(object):
    '''
    A class to hold results for a call to _stats: keeps all processed items and
    all subjects seen per subject type and provides helper methods to build and
    process those items.
    '''

    def __init__(self, items_definitions, subjects_patterns, log_handler=None):
        # Build items regular expression that will be used to match item names
        # and discover item types.
        items_re = dict((type, []) for type in TYPES)
        for item_re, item_type in items_definitions:
            items_re[item_type].append(item_re)
        self._items_patterns = dict(
            (type, re.compile(r'^(?:' + '|'.join(res) + r')$'))
            for type, res in items_re.items())

        # Set subject patterns that will be used to assign subject type and
        # subject values to items.
        self._subjects_patterns = subjects_patterns

        # Other initializations.
        self._log_handler = log_handler or sys.stderr.write
        self._items = {}
        self._subjects = {}

    @property
    def items(self):
        # Return all items that haven't had their value discarded because an
        # invalid aggregation.
        return (item for item in self._items.values() if item.value is not None)

    def add(self, name, value, type=None, subject_type=None,
            subject_value=None):
        # Add a new item to the internal state or simply aggregate it's value
        # if an item with the same name has already been added.
        if name in self._items:
            self._items[name].aggregate(value)
        else:
            # Build item.
            item = self._build_item(
                name, value, type, subject_type, subject_value)

            if item is not None:
                # Add new item to the internal state.
                self._items[item.name] = item

                # Also, register this item's subject in the corresponding set.
                if item.subject_type != None and item.subject_value != None:
                    if item.subject_type not in self._subjects:
                        self._subjects[item.subject_type] = set()
                    self._subjects[item.subject_type].add(item.subject_value)

    def get(self, name, default=None):
        # Return current value for a particular item or the given default value
        # if that item is not available or has had it's value discarded.
        if name in self._items and self._items[name].value is not None:
            return self._items[name].value
        else:
            return default

    def subjects(self, subject_type):
        # Return the set of registered subjects for a given subject type.
        return self._subjects.get(subject_type, set())

    def log(self, message):
        self._log_handler(message)

    def _build_item(
            self, name, value, type=None, subject_type=None,
            subject_value=None):
        # Initialize type if none was provided.
        if type is None:
            type = next((
                type for type in TYPES
                if self._items_patterns[type].match(name) is not None), None)

        # Filter invalid items.
        if type not in TYPES:
            return None

        # Initialize subject_type and subject_value if none were provided.
        if subject_type is None and subject_value is None:
            for subject, subject_re in self._subjects_patterns.items():
                if subject_re is not None:
                    match = subject_re.match(name)
                    if match is not None:
                        subject_type = subject
                        subject_value = match.group(1)
                        break

        # Return item instance.
        return Item(
            name=name,
            value=value,
            type=type,
            subject_type=subject_type,
            subject_value=subject_value
        )


def _stats(location, type, user, password):
    # Initializations.
    stats = Stats(ITEMS[type], SUBJECTS[type])
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

    # Authenticate as an user other than default?
    if user is not None:
        opts += ' --user "%s"' % user

    # Use password?
    if password is not None:
        opts += ' -a "%s"' % password

    # Fetch general stats through redis-cli.
    rc, output = _execute('redis-cli %(opts)s INFO %(section)s' % {
        'opts': opts,
        'section': 'all' if type == 'server' else 'default',
    })
    if rc == 0:
        section = None
        for line in output.splitlines():
            # Start of section. Keep it's name.
            if line.startswith('#'):
                section = line[1:].strip().lower()

            # Item. Process it.
            elif section is not None and ':' in line:
                # Extract item name and item value.
                key, value = (v.strip() for v in line.split(':', 1))
                if section == 'commandstats' and \
                   key.startswith('cmdstat_'):
                    key = key[8:].upper()
                name = '%s:%s' % (section, key)

                # If this item enables cluster mode set the corresponding flag
                # to later check for cluster stats.
                if name == 'cluster:cluster_enabled' and value == '1':
                    clustered = True

                # Special keys with subvalues.
                if ((type == 'server' and
                     section in ('keyspace', 'commandstats')) or \
                    (type == 'sentinel' and
                     section == 'sentinel' and
                     key.startswith('master'))):
                    # Extract subvalues.
                    subvalues = {}
                    for item in value.split(','):
                        if '=' in item:
                            subkey, subvalue = item.split('=', 1)
                            subvalues[subkey.strip()] = subvalue.strip()

                    # Process subvalues.
                    for subkey, subvalue in subvalues.items():
                        if type == 'sentinel' and subkey == 'name':
                            _stats_sentinel(
                                stats,
                                opts,
                                subvalue,
                                'masters:%s(%s)' % (key, subvalue))
                        else:
                            subname = None
                            if type != 'sentinel':
                                subname = '%s:%s' % (name, subkey)
                            elif subkey != 'name' and 'name' in subvalues:
                                subname = 'masters:%s(%s):%s' % (
                                    key, subvalues['name'], subkey)
                            if subname is not None:
                                # Add item to the result.
                                stats.add(subname, subvalue)

                # Simple keys with no subvalues.
                else:
                    # Add item to the result.
                    stats.add(name, value)

    # Error recovering information from redis-cli.
    else:
        stats.log(output)

    # Fetch cluster stats through redis-cli.
    if type == 'server' and clustered:
        _stats_cluster(stats, opts)

    # Done!
    return stats


def _stats_sentinel(stats, opts, master_name, prefix):
    # Fetch sentinel stats through redis-cli.
    rc, output = _execute('redis-cli %(opts)s SENTINEL ckquorum %(name)s' % {
        'opts': opts,
        'name': master_name,
    })
    if rc == 0:
        # Examples:
        #   - OK 3 usable Sentinels. Quorum and failover authorization can be
        #     reached.
        #   - NOQUORUM 1 usable Sentinels. Not enough available Sentinels to
        #     reach the majority and authorize a failover.
        stats.add(
            name='%s:ckquorum' % prefix,
            value='1' if output.startswith('OK') else '0')
        items = output.split(' ', 2)
        if len(items) >= 2 and items[1].isdigit():
            stats.add(
                name='%s:usable_sentinels' % prefix,
                value=items[1])

    # Error recovering information from redis-cli.
    else:
        stats.log(output)


def _stats_cluster(stats, opts):
    # Fetch cluster stats through redis-cli.
    rc, output = _execute('redis-cli %(opts)s CLUSTER INFO' % {
        'opts': opts,
    })
    if rc == 0:
        for line in output.splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                stats.add(
                    name='cluster:%s' % key.strip(),
                    value=value.strip())

    # Error recovering information from redis-cli.
    else:
        stats.log(output)


def _safe_zabbix_string(value):
    # Return a modified version of 'value' safe to be used as part of:
    #   - A quoted key parameter (see https://www.zabbix.com/documentation/5.0/manual/config/items/item/key).
    #   - A JSON string.
    return value.replace('"', '\\"')


def _execute(command, stdin=None):
    child = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    output = child.communicate(
        input=stdin.encode('utf-8') if stdin is not None else None)[0].decode('utf-8')
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
        '--redis-user', dest='redis_user',
        type=str, default=None,
        help='user name to be used in Redis instances authentication (redis >= 6.0)')
    parser.add_argument(
        '--redis-password', dest='redis_password',
        type=str, default=None,
        help='password required to access to Redis instances')
    subparsers = parser.add_subparsers(dest='command')

    # Set up 'stats' command.
    subparser = subparsers.add_parser(
        'stats',
        help='collect Redis stats')

    # Set up 'discover' command.
    subparser = subparsers.add_parser(
        'discover',
        help='generate Zabbix discovery schema')
    subparser.add_argument(
        'subject', type=str,
        help='dynamic resources to be discovered')

    # Parse command line arguments.
    options = parser.parse_args()

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
