from operator import itemgetter
from collections import OrderedDict

from django.forms.forms import pretty_name
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model

class ModelSearch(object):
    """
    ``model``: Reference to the model class for which a configuration is being provided.
    
    ``verbose_name``: An override to the model name for use in a frontend.
    
    ``display_fields``: An iterable of strings and/or 2-tuples, respectively describing model field
    names and ("Friendly name", "field_name"), for fields meant to be shown in a results table.
    Fields names in the first format, as a string lacking an explicit friendly name, will take on
    the ``verbose_name`` attribute of the field from the model's declaration.
    
    For example:
    
        display_fields = (
            'lot_number',
            ('Subdivision', 'subdivision__name'),
        )
    
    Fields included here are searchable by default and require no extra configuration.
    
    ``search_fields``: An iterable of single-item dictionaries, where each dictionary maps the
    access field name of a ForeignKey or other relationship field from the base ``model`` to a
    nested iterable.  The nested iterable may contain mixed loose items using the ``display_fields``
    formats or optionally another single-item dictionary mapping another related field name.
    
    Items described in ``search_fields`` are used in searches, but not the displayed results table
    when a search is performed.  As such, they will be presented to the frontend in a <select>
    element for the user to leverage when specifying search constraints.
    
    For example:
    
        search_fields = (
            {'subdivision': (
                'name',
                {'community': ('name',)}
            )},
        )
        
    The string 'subdivision' is understood to be the attribute found on a ``model`` instance.  On
    a hypothetical ``Subdivision`` class instance, one would find at least a ``name`` attribute and
    a ForeignKey to another model via the ``community`` attribute.  Further, this ``Community``
    model instance would itself have a ``name`` attribute.
    
    Using this configuration, the fields "subdivision__name" and "subdivision__community__name"
    would be included as searchable fields.
    
    Friendly names can be added to the example:
    
        search_fields = (
            {'subdivision: (
                ("Subdivision Code", 'name'),
                {'community': ('name',)}
            )},
        )
        
    If provided, the friendly name will appear in the frontend form.  Otherwise, the friendly name
    will be derived by taking the related model's verbose name and adding the field's verbose name.
    In this example, ``subdivision__name`` would appear as "Subdivision Code" (given by an explicit
    friendly name), but ``subdivision__community__name`` would appear as "Community Name".  However
    if Community's ``name`` field already had a model-defined verbose name "Title", the search UI
    would present the field as "Community Title".
    
    Adding more related fields is straightforward:
    
        search_fields = (
            {'subdivision: (
                'name',
                'city',
                {'community': ('name', 'state')},
            )},
            {'owner': (
                'username',
            )},
        )
    
    """
    
    model = None
    verbose_name = None
    
    display_fields = None
    search_fields = None
    
    _fields = None
    
    def __init__(self):
        self._process_searchable_fields()
        
        self._content_type = ContentType.objects.get_for_model(self.model)
    
    def _process_searchable_fields(self):
        """
        Crunches the information in ``display_fields`` and the intricate ``search_fields`` to
        produce a single consistent index of all searchable fields.
        
        The resulting index is formatted as an OrderedDict where keys are "friendly" readable names
        and are mapped to ORM-style paths such as "subdivision__name"
        
        """
        
        self._fields = OrderedDict()
        
        # Display fields
        
        # display_info = self._get_field_info([], self.model, None, self.display_fields, \
        #         include_model_in_verbose_name=False)
        # self._fields.update(display_info)
        
        # for field_info in self.display_fields:
        #     if not isinstance(field_info, (tuple, list)):
        #         field_name = field_info
        #         field, _, _, _ = self.model._meta.get_field_by_name(field_name)
        #         
        #         field_info = (field.verbose_name, field_name)
        #     
        #     verbose_name, field_name = field_info
        #     self._fields[field_name] = verbose_name
        
        
        # Search fields
        extended_info = self._get_field_info([], self.model, None, self.search_fields)
        self._fields.update(extended_info)
            
    def _get_field_info(self, orm_path_bits, model, related_name, field_list, include_model_in_verbose_name=True):
        """
        Recurses the fields listed on the model to provide a complete index of their ORM paths and
        friendly names.
            
        """
            
        # print
        # print "Getting field info for %s.%s fields: %r" % (model.__class__.__name__, related_name, field_list)
            
        if related_name:
            field, related_model, direct, m2m = model._meta.get_field_by_name(related_name)
            
            if related_model is None:# Field is local, follow the relationship to find the model
                # print field, related_model, direct, m2m
                if direct:
                    related_model = field.rel.to
                else:
                    related_model = field.model
        else:
            related_model = model
                
            
        base_orm_path = orm_path_bits
        sub_fields = []
            
        for field_name in field_list:
            # print "Handling field %r" % (field_name,)
            if isinstance(field_name, dict):
                # Nested dict.  Recurse the function with the new related context
                extended_name, sub_field_list = field_name.items()[0]
                orm_path_bits = base_orm_path
                if related_name:
                    orm_path_bits.append(related_name)
                sub_fields.extend(self._get_field_info(orm_path_bits, related_model, extended_name,\
                        sub_field_list))
            else:
                # Raw field name or 2-tuple
                
                # Check for a 2-tuple of ("Friendly name", "field_name")
                if isinstance(field_name, (tuple, list)):
                    verbose_name, field_name = field_name
                else:
                    # Derive a verbose name.  If the field comes from a model other than the base
                    # model, prepend the relate model's own verbose name.
                    field, _, _, _ = related_model._meta.get_field_by_name(field_name)
                    if related_name:
                        verbose_name_bits = [related_model._meta.verbose_name, field.verbose_name]
                    else:
                        verbose_name_bits = [field.verbose_name]
                    verbose_name = ' '.join(map(pretty_name, verbose_name_bits))
                    
                if related_name:
                    orm_path_bits = base_orm_path + [related_name, field_name]
                else:
                    orm_path_bits = base_orm_path + [field_name]
                sub_fields.append(['__'.join(orm_path_bits), verbose_name])
                # print orm_path_bits, field.name, related_model, verbose_name
                
            # print sub_fields
            
        return sub_fields    
    def get_model_name(self):
        """
        Gets the frontend-friendly name of the model represented by this configuration.
        
        By default, tries to return ``verbose_name``, then the ``model``'s verbose name.
        
        """
        
        if self.verbose_name:
            return self.verbose_name
        return pretty_name(self.model._meta.verbose_name)
    
    def get_operator_choices(self, field):
        """ Returns the list of django ORM query types that work for each search field. """
        
        pass
    
    # def get_searchable_fields(self):
    #     """ Returns the list of fields the model presents as searchable. """
    #     
    #     return self._fields.values()
    # 
    def get_searchable_field_choices(self):
        """ Returns an iterable of 2-tuples suitable for use as a form's ``choices`` attribute. """
        
        return self._fields.items()

class SearchRegistry(object):
    """
    Holds the gathered configurations from apps that use an appsearch.py module.
    
    """
    
    _registry = None
    # sort_function = lambda self, configurations: sorted(configurations, key=itemgetter(0))
    
    @staticmethod
    def get_from_list(cls, configuration_list):
        registry = SearchRegistry()
        for configuration in configuration_list:
            registry.register(configuration)
        return registry
    
    def __init__(self):
        self._registry = {}
    
    # def __getitem__(self, model):
    #     """ Old API compatibility. """
    #     return self._registry[model]
    # 
    # def keys(self):
    #     """ Old API compatibility. """
    #     return self._registry.keys()
    
    def __iter__(self):
        for k in self._registry:
            yield k
    
    def __getitem__(self, k):
        if isinstance(k, Model):
            k = k.__name__.lower()
        return self._registry[k]
    
    def register(self, model, configuration):
        if not isinstance(configuration, dict): # TODO: Remove this
            id_string = '.'.join((model._meta.app_label, model.__name__)).lower()
            self._registry[id_string] = configuration()
    
    def sort_function(self, configurations):
        return sorted(configurations, key=lambda c: c.model._meta.verbose_name)
    
    def set_sort_function(self, f):
        self.sort_function = f
    
    def sort_configurations(self, configurations):
        return self.sort_function(configurations)
    
    def get_configurations(self):
        """
        Hook for returning the registry data in a particular order.  By default, the configurations
        are returned in alphabetical order according to their model names.
        
        """
        
        return self.sort_configurations(self._registry.values())


search = SearchRegistry()
