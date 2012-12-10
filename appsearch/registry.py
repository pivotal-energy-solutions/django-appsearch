class SearchRegistry(object):
    """
    Holds the gathered configurations from apps that use an appsearch.py module.
    
    """
    
    _registry = None
    
    def __init__(self):
        self._registry = {}
    
    def __getitem__(self, model):
        """ Old API compatibility. """
        return self._registry[model]
    
    def keys(self):
        """ Old API compatibility. """
        return self._registry.keys()
    
    def register(self, model, search_configuration):
        self._registry[model.__name__.lower()] = search_configuration


search = SearchRegistry()
