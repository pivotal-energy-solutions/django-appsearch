# This code is heavily based on contrib.admin's autodiscover mechanism.

import logging
import sys

__name__ = 'appsearch'
__author__ = 'Pivotal Energy Solutions'
__version_info__ = (1, 1, "0-rc0")
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

    import copy
    from importlib import import_module

    from django.conf import settings
    from django.utils.module_loading import module_has_submodule
    from appsearch.registry import search


    for app in settings.INSTALLED_APPS:
        mod = import_module(app)
        # Attempt to import the app's appsearch module.
        try:
            before_import_registry = copy.copy(search._registry)
            import_module('%s.search' % app)
        except:
            # Reset the model registry to the state before the last import as
            # this import will have to reoccur on the next request and this
            # could raise NotRegistered and AlreadyRegistered exceptions
            # (see #8245).
            search._registry = before_import_registry

            # Decide whether to bubble up this error. If the app just
            # doesn't have an admin module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'search'):
                exc_type, e, traceback = sys.exc_info()
                raise exc_type, e.message, traceback
