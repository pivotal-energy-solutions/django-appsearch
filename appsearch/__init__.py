# This code is heavily based on contrib.admin's autodiscover mechanism.

import logging

log = logging.getLogger(__name__)

def autodiscover():
    """
    Auto-discover INSTALLED_APPS search.py modules and fail silently when
    not present. This forces an import on them to register any appsearch bits
    they may want.
    """

    import copy
    from django.conf import settings
    from django.utils.importlib import import_module
    from django.utils.module_loading import module_has_submodule
    from appsearch.registry import search

    for app in settings.INSTALLED_APPS:
        mod = import_module(app)
        # Attempt to import the app's appsearch module.
        try:
            before_import_registry = copy.copy(search._registry)
            import_module('%s.search' % app)
        except Exception as e:
            # Reset the model registry to the state before the last import as
            # this import will have to reoccur on the next request and this
            # could raise NotRegistered and AlreadyRegistered exceptions
            # (see #8245).
            search._registry = before_import_registry

            # Decide whether to bubble up this error. If the app just
            # doesn't have an admin module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'search'):
                
                log.warn("App %s.search failed to import.", app, exc_info=e)
                raise e
