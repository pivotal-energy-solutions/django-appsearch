from django.forms.formsets import formset_factory
from django.core.urlresolvers import reverse
from django.utils.encoding import StrAndUnicode
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
    
    string = None
    results = None
    
    def __init__(self, url, querydict, registry=search, **kwargs):
        self.kwargs = kwargs
        
        self._set_up_forms(querydict, registry)
        
        self.url = url
        self._determine_urls(kwargs)
        
        self.form_template = kwargs.get('form_template', 'appsearch/default_form.html')
    
    def __unicode__(self):
        return render_to_string(self.form_template, {
            self.kwargs.get('context_object_name', 'search'): self,
        })
    
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
