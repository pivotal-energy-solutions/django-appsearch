from django import forms
from django.forms import ValidationError
from django.forms.formsets import BaseFormSet
from django.db.models.fields import BLANK_CHOICE_DASH
from django.contrib.contenttypes.models import ContentType

from appsearch.registry import OPERATOR_MAP

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
    end_term = forms.CharField(label="End term", required=False)
    
    def __init__(self, configuration, *args, **kwargs):
        """
        Receives the configuration for the model to represent (potentially ``None`` if the original
        ``ModelSelectionForm`` is blank or invalid).
        
        """
        
        super(ConstraintForm, self).__init__(*args, **kwargs)
        
        self.configuration = configuration
        if configuration:
            self.fields['field'].choices = configuration.get_searchable_field_choices()
    
    def _clean_fields(self):
        """
        Workaround for displaying stripped info in the ``operator`` select, and running validation
        against reversed (name, value) choices.
        
        Because the frontend strips away the queryset language from the operator choices (leaving
        behind doubled 2-tuples of UI text such as ("= equal", "= equal")), the default field-level
        validation of the ``operator`` field will fail by default, since "iexact" is valid but
        "= equal" is not.  To solve the problem, this method sets the choices appropriately in
        reverse: ("= equal", "iexact").  When field validation inspects the value, everything will
        check out.  During that time, the ``clean_operator()`` method will be called to further
        process the ``operator`` value back to "iexact" (the reversed, faked UI text).
        
        Once all of the trickery is done, the choices are mapped once more to ("= equal", "= equal")
        so that when the template is rendered with this form, the choices are as they were before.
        
        """
        
        field_field = self.fields['field']
        field_hash = field_field.widget.value_from_datadict(self.data, {}, self.add_prefix('field'))
        operators = self.configuration.get_operator_choices(hash=field_hash)
        self.fields['operator'].choices = map(list, map(reversed, operators))
        
        # Allow default validation to occur, including the "clean_operator" method below.
        super(ConstraintForm, self)._clean_fields()
        
        # Set the operators back to the flat choices of frontend-only values
        self.fields['operator'].choices = map(lambda o: (o[1], o[1]), operators)
    
    def clean_field(self):
        """ Convert field into ORM path tuple. """
        data = self.cleaned_data['field']
        try:
            data = self.configuration.reverse_field_hash(data)
        except ValueError:
            raise ValidationError("Invalid choice")
        
        return data
    
    def clean_operator(self):
        """ Convert operator into ORM query type such as "icontains" """
        
        # The default cleaned_value will be the text from the UI, so the choices (which have been
        # reversed for default validation to accept the text as a valid choice) are converted to a
        # dictionary for accessing the intended ORM queryset language value.
        
        # Input: "= equal"
        # Output: "iexact"
        
        operator = self.cleaned_data['operator']
        operator = dict(self.fields['operator'].choices)[operator]
        
        return operator

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
