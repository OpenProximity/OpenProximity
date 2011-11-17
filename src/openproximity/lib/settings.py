# -*- coding: utf-8 -*-
# OpenProximity2.0 is a proximity marketing OpenSource system.
# Copyright (C) 2010,2009,2008 Naranjo Manuel Francisco <manuel@aircable.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from preset import *

# keep a reference to the parser
__CONFIGGLUE_PARSER__ = parser

from net.aircable.openproximity.pluginsystem import pluginsystem
pluginsystem.find_plugins(locals()['OP_PLUGINS'])

import plug
for k in dir(plug):
    if not k.isupper():
        continue
    locals()[k].extend(getattr(plug, k))
    orig=parser.get('django', k.lower())
    orig.extend(getattr(plug, k))
    parser.set('django', k.lower(), orig)

if not os.access(locals()['STORE_PATH'], os.W_OK):
    locals()['STORE_PATH'] = os.path.expanduser("~/.openproximity")

# make sure we don't get loaded again!
sys.modules['django-web.settings'] = sys.modules[__name__]

def __get_match_dongle(options, address):
    def __parse(option, typ=int):
        if len(option.strip()) == 0:
            return None
        return typ(option)

    address = address.lower().strip()
    for rang, val, enable, name in options:
        rang = rang.lower().strip()

        if address.startswith(rang):
            out = { 
                'enable': __parse(enable, bool), 
                'value': __parse(val), 
                'name': __parse(name, str) 
            }
            return out

GETSCANNERDONGLE=partial(__get_match_dongle, locals()['OP_SCANNERS'])
GETUPLOADERDONGLE=partial(__get_match_dongle, locals()['OP_UPLOADERS'])

class InvalidVarException(object):
    def __mod__(self, missing):
        try:
            missing_str=unicode(missing)
        except:
            missing_str='Failed to create string representation'
            raise Exception('Unknown template variable %r %s' % (
                    missing, missing_str))
    def __contains__(self, search):
        if search=='%s':
            return True
        return False
TEMPLATE_STRING_IF_INVALID = InvalidVarException()
