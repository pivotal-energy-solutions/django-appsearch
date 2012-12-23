import operator

from django.db.models.query import Q
from django.forms.formsets import formset_factory
from django.core.urlresolvers import reverse
from django.utils.encoding import StrAndUnicode
from django.template import RequestContext
from django.template.loader import render_to_string
from django.db.models.sql.constants import LOOKUP_SEP

from appsearch.registry import search, SearchRegistry
from appsearch.forms import ModelSelectionForm, ConstraintForm, ConstraintFormset

class Searcher(StrAndUnicode):
    """ Template helper, wrapping all the necessary components to render an appsearch page. """
    
    # Methods and fields not meant to be accessed from the template should start with an underscore
    # to let the template variable name resolution block access.
    
    model_selection_form = None
    constraint_formset = None
    
    field_data_url = None
    operator_data_url = None
    
    natural_string = None
    results = None
    
    # Processing callback hooks
    _display_fields_callback = None
    _process_results_callback = None
    
    ## Fallback items normally provided by the view
    context_object_name = 'search'
    
    # Default templates
    form_template_name = "appsearch/default_form.html"
    search_form_template_name = "appsearch/search_form.html"
    results_list_template_name = "appsearch/results_list.html"
    
    def __init__(self, request, url=None, querydict=None, registry=search, **kwargs):
        self.kwargs = kwargs
        self._request = request
        self.url = url or request.path
        self._determine_urls(kwargs)
        
        self._forms_ready = False
        self._set_up_forms(querydict or request.GET, registry)
        
        # Fallback items
        self.context_object_name = kwargs.get('context_object_name', self.context_object_name)
        self.form_template_name = kwargs.get('form_template_name', self.form_template_name)
        self.search_form_template_name = kwargs.get('search_form_template_name', self.search_form_template_name)
        self.results_list_template_name = kwargs.get('results_list_template_name', self.results_list_template_name)
        
        self._display_fields_callback = kwargs.get('display_fields_callback')
        self._process_results_callback = kwargs.get('process_results_callback')
    
    # Rendering methods
    def __unicode__(self):
        return render_to_string(self.form_template_name, RequestContext(self._request, {
            self.context_object_name: self,
        }))
    
    def render_search_form(self):
        """ Renders only the template at ``search_form_template_name`` """
        return render_to_string(self.search_form_template_name, RequestContext(self._request, {
            self.context_object_name: self,
        }))
    
    def render_results_list(self):
        """ Renders only the template at ``results_list_template_name`` """
        return render_to_string(self.results_list_template_name, RequestContext(self._request, {
            self.context_object_name: self,
        }))
    
    @property
    def ready(self):
        """ Indicates if a search has been executed by the constructed state. """
        
        if self._forms_ready:
            self.model_config = self.model_selection_form.get_selected_configuration()
            self.model = self.model_config.model
        
        return self._forms_ready
        
    def _set_up_forms(self, querydict, registry):
        self.model_selection_form = ModelSelectionForm(registry, querydict)
        constraint_formset_class = formset_factory(ConstraintForm, formset=ConstraintFormset)
        
        if self.model_selection_form.is_valid():
            model_configuration = self.model_selection_form.get_selected_configuration()
            self.constraint_formset = constraint_formset_class(model_configuration, querydict)
            if self.constraint_formset.is_valid():
                self._forms_ready = True
        else:
            self.model_selection_form = ModelSelectionForm(registry)
            self.constraint_formset = constraint_formset_class(configuration=None)
    
    def _determine_urls(self, kwargs):
        # If a URL is not customized, this namespace will be used to search out the default URL
        url_namespace = kwargs.get('url_namespace')
        
        # Check custom data URLs
        field_url = kwargs.get('field_url')
        operator_url = kwargs.get('operator_url')
        
        if field_url is None:
            url_name = 'appsearch:constraint-fields'
            if url_namespace is not None:
                url_name = url_namespace + ':' + url_name
            field_url = reverse(url_name, kwargs=kwargs.get('field_url_kwargs', {}))
        if operator_url is None:
            url_name = 'appsearch:constraint-operators'
            if url_namespace is not None:
                url_name = url_namespace + ':' + url_name
            operator_url = reverse(url_name, kwargs=kwargs.get('operator_url_kwargs', {}))
        
        self.field_data_url = field_url
        self.operator_data_url = operator_url
    
    def _perform_search(self):
        """
        Generates the query using the validated constraint formset.  Also compiles a natural
        language string (``self.natural_string``) in the format of
        "N [Model]s with [field] [operator] '[term]'".
        
        """
        
        self.natural_string = self.model_config.verbose_name_plural
        
        # 2-tuples of an operator and Q instance, sent through reduce() after it's built
        query_list = []
        
        for i, constraint_form in enumerate(self.constraint_formset):
            type = constraint_form.cleaned_data['type']
            field_list = constraint_form.cleaned_data['field']
            constraint_operator = constraint_form.cleaned_data['operator']
            term = constraint_form.cleaned_data['term']
            end_term = constraint_form.cleaned_data['end_term']
            
            if type == 'and':
                type_operator = operator.and_
            elif type == 'or':
                type_operator = operator.or_
            
            # Build this field's query.
            # Search fields bound together in a tuple are considered OR conditions for a single
            # virtual field name.
            query = None
            for field in field_list:
                value = term
                
                # Prep an inverted lookup
                negative = constraint_operator.startswith('!')
                if negative:
                    constraint_operator = constraint_operator[1:]
                
                # Adapt the terms for the operator
                if operator == "range":
                    value = [value, end_term]
                # elif operator == "iexact":
                #     value = 
                
                # Bake the queryset language string
                field_query = LOOKUP_SEP.join((field, constraint_operator))
                
                q = Q(**{
                    field_query: value,
                })
                
                # Negate if necessary
                if negative:
                    q = ~q
                
                if query is None:
                    query = q
                else:
                    query |= q
            
            query_list.append((type_operator, query))
        
        # The first query's "type" should be ignored for the sake of the reduce line below.
        query_list[0] = query_list[0][1]
        query = reduce(lambda q1, (op, q2): op(q1, q2), query_list)
        
        queryset = self.model.objects.filter(query)
        queryset = self.process_queryset(queryset)
        data_rows = self.process_results(queryset)
        
        self.results = {
            'count': len(queryset),
            'list': data_rows,
            'fields': self.get_display_fields(),
        }
    
    def get_display_fields(self):
        if self._display_fields_callback:
            return self._display_fields_callback(self, self.model, self.model_config)
        return self.model_config.get_display_fields()
    
    def process_queryset(self, queryset):
        """
        Hook for selecting necessary related fields on the given ``queryset``.
        
        Default behavior inspects the display fields for any related items and requests their
        selection.
        
        """
        
        display_fields = self.get_display_fields()
        related_names = set()
        for field_info in display_fields:
            if isinstance(field_info, (tuple, list)):
                _, field_name = field_info
            else:
                field_name = field_info
            
            related_path = field_name.rsplit(LOOKUP_SEP, 1)[0]
            
            if LOOKUP_SEP in related_path:
                related_names.add(related_path)
        
        return queryset.select_related(*related_names)
    
    def process_results(self, queryset):
        """
        Converts the instances in ``object_list`` to a list of 1-tuples.  Provided as a hook for a
        view subclass to override and provide appropriate behavior.
        
        Should return a sequence of n-tuples, where ``n`` is the number of columns to be shown in
        the table.
        
        """
        
        if self._process_results_callback:
            self._process_results_callback(self, self.model, self.model_config, queryset)
        
        return [self.model_config.get_object_data(obj) for obj in queryset]
