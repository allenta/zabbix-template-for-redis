# -*- coding: utf-8 -*-

'''
:url: https://github.com/allenta/zabbix-template-for-redis
:copyright: (c) 2015-2022 by Allenta Consulting S.L. <info@allenta.com>.
:license: BSD, see LICENSE.txt for more details.
'''

import binascii
import hashlib
from jinja2.ext import Extension


class ZabbixExtension(Extension):
    uuids = set()

    def __init__(self, environment):
        super(ZabbixExtension, self).__init__(environment)
        environment.filters['zuuid'] = self._zuuid

    def _zuuid(self, seed):
        data = bytearray(hashlib.md5(seed.encode('utf-8')).digest())
        data[6] = data[6] & 0x0f | 0x40
        data[8] = data[8] & 0x3f | 0x80
        uuid = binascii.hexlify(data).decode('utf-8')

        if uuid in self.uuids:
            raise Exception("Duplicated seed/UUID: '{}' ➙ {}".format(seed, uuid))
        self.uuids.add(uuid)

        return uuid
