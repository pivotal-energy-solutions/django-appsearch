from django.forms.formsets import formset_factory
from django.core.urlresolvers import reverse
from django.utils.encoding import StrAndUnicode
from django.template import RequestContext
from django.template.loader import render_to_string

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
        
        self._set_up_forms(querydict or request.GET, registry)
        self._determine_urls(kwargs)
        
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
    
    def _set_up_forms(self, querydict, registry):
        self.model_selection_form = ModelSelectionForm(registry, querydict)
        constraint_formset_class = formset_factory(ConstraintForm, formset=ConstraintFormset)
        
        if self.model_selection_form.is_valid():
            model_configuration = self.model_selection_form.get_model_configuration()
            self.constraint_formset = constraint_formset_class(model_configuration, querydict)
            if self.constraint_formset.is_valid():
                # TODO: Execute search machinery
                pass
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
