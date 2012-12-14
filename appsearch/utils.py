from django.forms.formsets import formset_factory

from appsearch.registry import search, SearchRegistry
from appsearch.forms import ModelSelectionForm, ConstraintForm, ConstraintFormset

class Searcher(object):
    model_selection_form = None
    constraint_formset = None
    
    string = None
    results = None
    
    def __init__(self, params, registry=search):
        self.set_up_forms(params, registry)
    
    def set_up_forms(self, params, registry):
        self.model_selection_form = ModelSelectionForm(registry, params)
        constraint_formset_class = formset_factory(ConstraintForm, formset=ConstraintFormset)
        
        if self.model_selection_form.is_valid():
            model_configuration = self.model_selection_form.get_model_configuration()
            self.constraint_formset = constraint_formset_class(model_configuration, params)
            if self.constraint_formset.is_valid():
                # TODO: Execute search machinery
                pass
        else:
            self.model_selection_form = ModelSelectionForm(registry)
            self.constraint_formset = constraint_formset_class(configuration=None)
