# -*- coding: utf-8 -*-
"""forms.py: appsearch forms"""

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import operator

from django import forms
from django.forms import ValidationError
from django.forms.formsets import BaseFormSet
from django.db.models.fields import BLANK_CHOICE_DASH
from django.contrib.contenttypes.models import ContentType

import dateutil.parser


class ModelSelectionForm(forms.Form):
    """
    Default Model selection form.

    Builds choices based on the registered configurations in the given ``registry``.  The form uses
    content type ids for values instead of model names or module paths, etc.

    """

    model = forms.ChoiceField(label="Search For")

    def __init__(self, registry, user, permission, *args, **kwargs):
        super(ModelSelectionForm, self).__init__(*args, **kwargs)

        self.registry = registry
        self.configurations = registry.get_configurations(user=user, permission=permission)

        self.fields['model'].choices = BLANK_CHOICE_DASH + \
            [(c._content_type.id, c.verbose_name) for c in self.configurations]

    def clean_model(self):
        """ Cleans the content type id into the model it represents. """
        model = self.cleaned_data['model']
        try:
            model = ContentType.objects.get(id=model).model_class()
        except ContentType.DoesNotExist as e:
            raise ValidationError("Invalid choice - {}".format(e))
        if model not in self.registry:
            raise ValidationError("Invalid choice")
        return model

    def get_selected_configuration(self):
        """
        Given that the form has passed validation, returns the configuration for the selected model.

        """
        model_value = self.cleaned_data['model']
        return self.registry[model_value]

    def get_selected_model(self):
        """ Given that the form has passed validation, returns the selected model. """
        return self.get_selected_configuration().model


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

    term = forms.CharField(label="Search term", required=False)
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

    def clean_type(self):
        """ Convert type into an ``operator.and_`` or ``operator.or_`` reference. """

        type = self.cleaned_data['type']

        if type == "and":
            type = operator.and_
        elif type == "or":
            type = operator.or_

        return type

    def clean_field(self):
        """ Convert ``field`` hash into ORM path tuple. """
        return self.configuration.reverse_field_hash(self.cleaned_data['field'])

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

    def clean_term(self):
        """ Normalizes the ``term`` field to what makes sense for the operator. """

        if 'field' not in self.cleaned_data or 'operator' not in self.cleaned_data:
            return self.cleaned_data['term']

        classification = self.configuration.get_field_classification(self.cleaned_data['field'])
        operator = self.cleaned_data['operator']
        term = self.cleaned_data['term'].strip()
        field_type = self.configuration.field_types[self.cleaned_data['field']]

        if field_type.choices:
            # The field's database values aren't the display values, but the display values are
            # what the user will search for.  e.g., choices=[(1, 'Bob'), (2, 'Mary')]
            choices = {k.lower(): v for v, k in field_type.choices}
            if term.lower() in choices:
                term = choices[term.lower()]
        else:
            # Numbers and strings don't need processing, but the other types should be inspected.
            if classification == "date":
                try:
                    term = dateutil.parser.parse(term)
                except (TypeError, ValueError):
                    raise ValidationError("Unable to parse a date from '{}'".format(term))
            elif classification == "boolean":
                if term.lower() in ("true", "yes"):
                    term = True
                elif term.lower() in ("false", "no"):
                    term = False
                else:
                    raise ValidationError("Boolean value must be either true/false or yes/no.")
            elif classification == "number":
                try:
                    float(term)
                except:
                    raise ValidationError("Value must be numeric.")

        if operator not in ('isnull', '!isnull') and term in [None, '']:
            raise ValidationError("This field is required.")

        return term

    def clean_end_term(self):
        """
        Normalize the ``end_term`` field for range queries.

        The ``end_term`` will merge itself into ``term`` if appropriate, making the cleaned value
        of ``term`` a list of the two values suitable for direct use in a queryset "range" lookup.
        Consequently, ``end_term`` will always clean to the empty string.

        """

        if 'field' not in self.cleaned_data or 'operator' not in self.cleaned_data \
                or 'term' not in self.cleaned_data:
            return self.cleaned_data['end_term']

        classification = self.configuration.get_field_classification(self.cleaned_data['field'])
        operator = self.cleaned_data['operator']
        begin_term = self.cleaned_data['term']
        term = self.cleaned_data['end_term']

        if operator == "range":
            if classification == "date":
                term = dateutil.parser.parse(term)
            elif classification == "number":
                term = int(term)
            else:
                raise ValidationError("Unknown range type %r." % classification)
            self.cleaned_data['term'] = [begin_term, term]

        return ""


class ConstraintFormset(BaseFormSet):
    """ Removes the first ``ConstraintForm``'s ``type`` field. """

    def __init__(self, configuration, *args, **kwargs):
        """ Stores the configuration until the forms are constructed. """
        self.configuration = configuration
        super(ConstraintFormset, self).__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        """ Sends the specified model configuration to the form. """
        return super(ConstraintFormset, self)._construct_form(i, configuration=self.configuration,
                **kwargs)
