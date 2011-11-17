"""
Some OpenProximity context variables that are some times
required
"""
import os
from django.conf import settings
try:
    from openproximity import __version__ as opversion
except:
    opversion = 'ND'

def variables(requesst):
    return {
        'version': { 'current': opversion },
        'settings': {
            'logo': settings.OP_LOGO,
            'debug': settings.OP_DEBUG,
            'translate': settings.OP_TRANSLATE,
            'twitter': settings.OP_TWITTER
        }
    }
