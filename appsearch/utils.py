import operator
import logging

from django.db.models.query import Q
from django.forms.formsets import formset_factory
from django.core.urlresolvers import reverse
from django.utils.encoding import StrAndUnicode
from django.template import RequestContext
from django.template.loader import render_to_string
from django.db.models.sql.constants import LOOKUP_SEP

from appsearch.registry import search, SearchRegistry
from appsearch.forms import ModelSelectionForm, ConstraintForm, ConstraintFormset

log = logging.getLogger(__name__)

class Searcher(StrAndUnicode):
    """ Template helper, wrapping all the necessary components to render an appsearch page. """
    
    # Methods and fields not meant to be accessed from the template should start with an underscore
    # to let the template variable name resolution block access.
    
    # Customizable classes
    model_selection_form_class = ModelSelectionForm
    constraint_form_class = ConstraintForm
    constraint_formset_class = ConstraintFormset
    
    # Instance data
    model_selection_form = None
    constraint_formset = None
    
    field_data_url = None
    operator_data_url = None
    
    results = None
    
    # Processing callback hooks
    _display_fields_callback = None
    _build_queryset_callback = None
    _process_results_callback = None
    
    ## Fallback items normally provided by the view
    context_object_name = 'search'
    
    # Default templates
    form_template_name = "appsearch/default_form.html"
    search_form_template_name = "appsearch/search_form.html"
    results_list_template_name = "appsearch/results_list.html"
    
    def __init__(self, request, url=None, querydict=None, registry=search, **kwargs):
        self.kwargs = kwargs
        self.request = request
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
        self._build_queryset_callback = kwargs.get('build_queryset_callback')
        self._process_results_callback = kwargs.get('process_results_callback')
    
    # Rendering methods
    def __unicode__(self):
        return render_to_string(self.form_template_name, RequestContext(self.request, {
            self.context_object_name: self,
        }))
    
    def render_search_form(self):
        """ Renders only the template at ``search_form_template_name`` """
        return render_to_string(self.search_form_template_name, RequestContext(self.request, {
            self.context_object_name: self,
        }))
    
    def render_results_list(self):
        """ Renders only the template at ``results_list_template_name`` """
        return render_to_string(self.results_list_template_name, RequestContext(self.request, {
            self.context_object_name: self,
        }))
    
    
    def get_model_selection_form_class(self):
        """ Returns ``self.model_selection_form_class`` """
        return self.model_selection_form_class
    
    def get_constraint_form_class(self):
        """ Returns ``self.constraint_form_class`` """
        return self.constraint_form_class
    
    def get_constraint_formset_class(self):
        """ Returns ``self.constraint_formset_class`` """
        return self.constraint_formset_class
    
    @property
    def ready(self):
        """ Indicates if a search has been executed by the constructed state. """
        
        if self._forms_ready:
            self.model_config = self.model_selection_form.get_selected_configuration()
            self.model = self.model_config.model
        
        return self._forms_ready
        
    def _set_up_forms(self, querydict, registry, permission=None):
        ModelSelectionFormClass = self.get_model_selection_form_class()
        ConstraintFormClass = self.get_constraint_form_class()
        ConstraintFormsetClass = self.get_constraint_formset_class()
        
        ConstraintFormsetClass = formset_factory(ConstraintFormClass, formset=ConstraintFormsetClass)
        
        self.model_selection_form = ModelSelectionFormClass(registry, self.request.user, permission,
                querydict)
        
        if self.model_selection_form.is_valid():
            model_configuration = self.model_selection_form.get_selected_configuration()
            self.constraint_formset = ConstraintFormsetClass(model_configuration, querydict)
            if self.constraint_formset.is_valid():
                self._forms_ready = True
        else:
            self.model_selection_form = ModelSelectionFormClass(registry, self.request.user,
                    permission)
            self.constraint_formset = ConstraintFormsetClass(configuration=None)
    
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
        
        natural_string = []
        
        # 2-tuples of an operator and Q instance, sent through reduce() after it's built
        query_list = []
        
        for i, constraint_form in enumerate(self.constraint_formset):
            type_operator = constraint_form.cleaned_data['type']
            field_list = constraint_form.cleaned_data['field']
            constraint_operator = constraint_form.cleaned_data['operator']
            term = constraint_form.cleaned_data['term']
            end_term = constraint_form.cleaned_data['end_term']
            
            verbose_name = self.model_config._fields[field_list]
            
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
                
                if constraint_operator == "isnull":
                    value = not negative
                    negative = False
                
                # Bake the queryset language string
                field_query = LOOKUP_SEP.join((field, constraint_operator))
                
                q = Q(**{
                    field_query: value,
                })
                
                log.debug("Querying %s [%d]: %s=%r", self.model.__name__, i, field_query, value)
                
                # Negate if necessary
                if negative:
                    q = ~q
                
                if query is None:
                    query = q
                else:
                    query |= q
                
            query_list.append((type_operator, query))
            
            # Do some natural processing
            if isinstance(value, (tuple, list)):
                value = ' - '.join(map(unicode, value))
            else:
                value = str(value)
            bits = [verbose_name, constraint_form['operator'].value(), value]
            if i != 0: # Skip the leading "and" on the first constraint
                bits.insert(0, constraint_form['type'].value())
            natural_string.append(bits)
        
        # The first query's "type" should be ignored for the sake of the reduce line below.
        query = reduce(lambda q1, (op, q2): op(q1, q2), query_list[1:], query_list[0][1])
        
        queryset = self.build_queryset(self.model, query)
        data_rows = self.process_results(queryset)
        
        self.results = {
            'count': len(queryset),
            'list': data_rows,
            'fields': self._get_display_fields(self.model, self.model_config),
            'natural_string': "where " + ', '.join(map(' '.join, natural_string)),
        }
    
    def _get_display_fields(self, model, config):
        if self._display_fields_callback:
            return self._display_fields_callback(self, model, config)
        return config.get_display_fields()
    
    def get_select_related_fields(self, model, config):
        """ Returns a list of queryset language names to pass into ``.select_related()`` """
        display_fields = self._get_display_fields(model, config)
        related_names = set()
        for field_info in display_fields:
            if isinstance(field_info, (tuple, list)):
                _, field_name = field_info
            else:
                field_name = field_info
            
            related_path = field_name.rsplit(LOOKUP_SEP, 1)[0]
            
            if LOOKUP_SEP in related_path:
                related_names.add(related_path)
        
        return related_names
    
    def build_queryset(self, model, query, queryset=None):
        """
        Returns the queryset using ``query``.
        
        Default behavior inspects the display fields for any related items and requests their
        selection and adds ``.distinct()``.
        
        If ``base_queryset`` is provided, it will be used as the starting point for applying the
        ``query`` filter.  This is useful for subclasses that want to change the default manager
        being accessed for the initial queryset.  Passing up a ``queryset`` via super() will
        accomplish this, returning a fully built queryset with minimum hassle.
        
        If ``build_queryset`` callback was defined on the originating view, it will be called
        after the queryset is built and will be sent the searcher instance, model, config, initial
        ``Q`` query, and the derived queryset.  The callback should return the queryset in its final
        state for execution.
        
        """
        
        related_names = self.get_select_related_fields(model, self.model_config)
        
        if queryset is None:
            queryset = self.model_config.get_queryset(self.request.user)
        
        queryset = queryset.filter(query).select_related(*related_names).distinct()
        
        if self._build_queryset_callback:
            queryset = self._build_queryset_callback(self, model, self.model_config, query,
                    queryset)
        
        return queryset
    
    def process_results(self, queryset):
        """
        Should return a sequence of n-tuples, where ``n`` is the number of columns to be shown in
        the table.
        
        """
        
        if self._process_results_callback:
            return self._process_results_callback(self, self.model, self.model_config, queryset)
        
        return [self.model_config.get_object_data(obj) for obj in queryset]
