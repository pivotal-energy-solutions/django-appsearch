# This code is heavily based on contrib.admin's autodiscover mechanism.

import logging
import sys

__name__ = 'appsearch'
__author__ = 'Pivotal Energy Solutions'
__version_info__ = (1, 1, 3)
__version__ = '.'.join(map(str, __version_info__))
__date__ = '2014/07/22 4:47:00 PM'
__credits__ = ['Tim Valenta', "Steven Klass"]
__license__ = 'See the file LICENSE.txt for licensing information.'

log = logging.getLogger(__name__)

def autodiscover():
    """
    Auto-discover INSTALLED_APPS search.py modules and fail silently when
    not present. This forces an import on them to register any appsearch bits
    they may want.
    """

    from importlib import import_module
    from django.apps import apps
    from django.utils.module_loading import module_has_submodule
    from appsearch.registry import search

    for config in apps.get_app_configs():
        if module_has_submodule(config.module, 'search'):
            try:
                mod = import_module(config.name + '.search')
            except:
                exc_type, e, traceback = sys.exc_info()
                raise exc_type, e.message, traceback
