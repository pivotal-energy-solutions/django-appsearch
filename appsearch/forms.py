from django import forms
from django.forms import ValidationError
from django.forms.formsets import BaseFormSet
from django.db.models.fields import BLANK_CHOICE_DASH

OPERATOR_CHOICES = [
    ("__lt", "<"),
    ("__gt", ">"),
    ("__iexact", "="),
    ('__icontains', "contains"),
    ('__range', "range" ),
    ('__isnull', "exists" ),
    ('__isnotnull', "doesn't exist" ),
]

class ModelSelectionForm(forms.Form):
    model = forms.ChoiceField(label="Search For")
    
    def __init__(self, registry, *args, **kwargs):
        self.registry = registry
        configurations = registry.get_configurations()
        super(ModelSelectionForm, self).__init__(*args, **kwargs)
        
        self.fields['model'].choices = BLANK_CHOICE_DASH + \
                [(c._content_type.id, c.verbose_name) for c in configurations]
    
    def clean_model(self):
        model = self.cleaned_data['model']
        try:
            model = ContentType.objects.get(id=model).model_class()
        except ContentType.DoesNotExist as e:
            raise ValidationError("Invalid choice")
        
        if model not in self.registry:
            raise ValidationError("Invalid choice")
        
        return model
    
    def get_selected_configuration(self):
        model_value = self.cleaned_data['model']
        return self.registry[model_value]
    
    def get_selected_model(self):
        """ Returns the select model's class. """
        
        return self.get_selected_configuration().model

class SearchForm(object):
    pass


class ConstraintForm(forms.Form):
    """
    Using an additional constructor parameter ``configuration``, an instance of
    ``registry.ModelSearch``, the form dynamically populates the choices for the ``field`` field.
    
    """
    
    type = forms.ChoiceField(label="Constraint", choices=[
        ('and', 'AND'),
        ('or', 'OR'),
    ])
    
    # Dynamically populated list of fields available for filtering
    field = forms.ChoiceField(label="Filter by", choices=[])
    
    # Dynamically populated list of valid operators for the chosen ``field``
    operator = forms.ChoiceField(label="Constraint type", choices=[])
    
    term = forms.CharField(label="Search term")
    end_term = forms.CharField(label="End term")
    
    def __init__(self, configuration, *args, **kwargs):
        """
        Receives the configuration for the model to represent (potentially ``None`` if the original
        ``ModelSelectionForm`` is blank or invalid).
        
        """
        
        super(ConstraintForm, self).__init__(*args, **kwargs)
        
        self.configuration = configuration
        if configuration:
            self.field.choices = configuration.get_searchable_field_choices()
            # self.operator.choices = map(map(itemgetter, configuration.get_orm_operators()), OPERATOR_CHOICES)
    def clean_field(self):
        data = self.cleaned_data['field']
        try:
            data = self.configuration.reverse_field_hash(data)
        except ValueError:
            raise ValidationError("Invalid field")
        
        return data

class ConstraintFormset(BaseFormSet):
    """ Removes the first ``ConstraintForm``'s ``type`` field. """
    
    def __init__(self, configuration, *args, **kwargs):
        """ Stores the configuration until the forms are constructed. """
        self.configuration = configuration
        super(ConstraintFormset, self).__init__(*args, **kwargs)
    
    def _construct_form(self, i, **kwargs):
        """ Sends the specified model configuration to the form. """
        return super(ConstraintFormset, self)._construct_form(i, configuration=self.configuration, \
                **kwargs)
    
    # def add_fields(self, form, index):
    #     """ Removes the first form's ``type`` field. """
    #     super(ConstraintFormset, self).add_fields(form, index)
    #     if index == 0:
    #         del form.fields['type']
