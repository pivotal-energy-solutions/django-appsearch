# -*- coding: utf-8 -*-
"""utils.py: Searcher"""

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import logging
import json
from operator import itemgetter
from collections import defaultdict

from django.db.models.query import Q
from django.forms.formsets import formset_factory
from django.template import RequestContext
from django.template.loader import render_to_string
try:
    from django.db.models.sql.constants import LOOKUP_SEP
except:
    from django.db.models.constants import LOOKUP_SEP
from django.utils.safestring import mark_safe

from .registry import search, SearchRegistry
from .forms import ModelSelectionForm, ConstraintForm, ConstraintFormset
from .ormutils import resolve_orm_path

log = logging.getLogger(__name__)


class Searcher(object):
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

    def __init__(self, request, url=None, querydict=None, registry=search, permission=None, **kwargs):
        self.kwargs = kwargs
        self.request = request
        self.url = url or request.path

        self._forms_ready = False
        self._set_up_forms(querydict or request.GET, registry, permission)
        self.permission = permission
        self.registry = registry

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
        return render_to_string(self.form_template_name,
                                RequestContext(self.request, {self.context_object_name: self}).flatten())

    def render_search_form(self):
        """ Renders only the template at ``search_form_template_name`` """
        return render_to_string(self.search_form_template_name,
                                RequestContext(self.request, {self.context_object_name: self, }).flatten())

    def render_results_list(self):
        """ Renders only the template at ``results_list_template_name`` """
        return render_to_string(self.results_list_template_name,
                                RequestContext(self.request, {self.context_object_name: self, }).flatten())

    def render_constraint_fields(self, model):
        """ Renders into JSON the model's fields available for search queries. """

        configuration = self.registry.get_configuration(model)
        choices = configuration.get_searchable_field_choices(include_types=True)
        return json.dumps({'choices': choices})

    def get_constraint_field_operators(self, model, field=None, hash=None):
        """ Returns into JSON the model's field's valid search operators. """

        if field is None and hash is None:
            raise ValueError("Need one of 'field' or 'hash'.")

        configuration = self.registry.get_configuration(model)

        # Fetch the choices without the query orm language.  Only UI labels are used at this stage.
        choices = configuration.get_operator_choices(field=field, hash=hash, flat=True)
        return choices

    def render_all_constraint_choices(self):
        """
        Returns a mapping of all models to their field choices, and all models to field hashes to
        operators.

        """

        field_data = defaultdict(list)
        operator_data = defaultdict(dict)

        configurations = self.model_selection_form.configurations
        model_values = map(itemgetter(0), self.model_selection_form.fields['model'].choices)[1:]

        for model_value, config in zip(model_values, configurations):
            model = config.model
            field_choices = config.get_searchable_field_choices(include_types=True)
            for orm_hash, field_label, field_type in field_choices:
                operator_choices = self.get_constraint_field_operators(model, hash=orm_hash)
                field_data[model_value].append([orm_hash, field_label, field_type])
                operator_data[model_value][orm_hash] = operator_choices

        return mark_safe(json.dumps({
            'fields': field_data,
            'operators': operator_data,
        }))

    # Configuration methods
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

            # Iterate multiple fields defined in a compound column
            for field in field_list:
                value = term
                target_field = resolve_orm_path(self.model, field)

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
                log.debug("Querying %s [%d]: %s%s=%r", self.model.__name__, i, field_query,
                          "!" if negative else "", value)

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
        display_fields = config._display_fields
        related_names = set()
        for _, field_name, _ in display_fields:
            name_bits = field_name.rsplit(LOOKUP_SEP, 1)
            if len(name_bits) == 2:
                related_names.add(name_bits[0])

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
            queryset = self.model_config.get_queryset(self.request, self.request.user)

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
