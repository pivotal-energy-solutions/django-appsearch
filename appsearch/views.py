# coding=utf-8
import json

from django.views.generic import View, TemplateView
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType

from appsearch.utils import Searcher
from appsearch.registry import search


class SearchMixin(object):
    searcher_class = Searcher

    context_object_name = 'search'
    form_template_name = "appsearch/default_form.html"
    search_form_template_name = "appsearch/search_form.html"
    results_list_template_name = "appsearch/results_list.html"

    # Callbacks, unprovided by default
    get_display_fields = None
    build_queryset = None
    process_results = None

    def get_context_data(self, **kwargs):
        context = super(SearchMixin, self).get_context_data(**kwargs)

        object_name = self.get_context_object_name()
        searcher = self.get_searcher()

        if searcher.ready:
            searcher._perform_search()

        context[object_name] = searcher
        return context

    def get_searcher_class(self):
        """ Returns the view's ``searcher_class`` attribute. """
        return self.searcher_class

    def get_searcher(self):
        """ Builds and returns a ``Searcher`` instance for this search context. """
        return self.get_searcher_class()(self.request, **self.get_searcher_kwargs())

    def get_searcher_kwargs(self):
        """ Returns the dictionary of kwargs sent to the ``Searcher`` constructor. """

        return {
            'form_template_name': self.get_form_template_name(),
            'search_form_template_name': self.get_search_form_template_name(),
            'results_list_template_name': self.get_results_list_template_name(),
            'context_object_name': self.get_context_object_name(),

            # Callbacks
            'display_fields_callback': self.get_display_fields,
            'build_queryset_callback': self.build_queryset,
            'process_results_callback': self.process_results,
        }

    def get_context_object_name(self):
        return self.context_object_name

    def get_form_template_name(self):
        return self.form_template_name

    def get_search_form_template_name(self):
        return self.search_form_template_name

    def get_results_list_template_name(self):
        return self.results_list_template_name

class BaseSearchView(SearchMixin, TemplateView):
    pass


class BaseAjaxConfigurationResolutionView(View):
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

        model = kwargs.get('model', request.GET.get('model'))

        config, response = self.resolve_configuration(request, model)

        if config is None:
            return response

        self.configuration = config

        return super(BaseAjaxConfigurationResolutionView, self).dispatch(request, model=model)

    def resolve_configuration(self, request, model):
        if not request.is_ajax() and request.GET.get('ajax') != 'true':
            return None, HttpResponseBadRequest("Bad Request")

        if model is None:
            return None, HttpResponseBadRequest("No model is supplied")

        try:
            content_type = ContentType.objects.get(id=model)
        except (ValueError, ContentType.DoesNotExist):
            content_type = None
            model = None
            model_class = None
        else:
            model = '.'.join((content_type.app_label, content_type.model))
            model_class = content_type.model_class()

        if model_class and model in search:
            configuration = search[model]
            model_perm = configuration.user_has_perm(self.request.user)
            if model_perm is False or \
                    model_perm is None and self.has_perm(model_class) is False:
                configuration = None
        else:
            configuration = None

        if not configuration:
            return None, HttpResponseForbidden()

        return configuration, None

    def has_perm(self, model_class):
        """
        Attempts a lookup of ``model_class`` in the registry.  By sending the ``user`` argument to
        the lookup, the user's permissions will be compared to the registry's own ``permission``
        attribute.

        The view cannot specify its own permission value here because the view doesn't build or
        control the registry or the model selection form; if the permission check needs to be
        modified, the template string at ``registry.permission`` should be updated.

        """
        configuration = search.get_configuration(model_class, user=self.request.user)

        return configuration is not None

class ConstraintFieldsAjaxView(BaseAjaxConfigurationResolutionView):
    """
    Looks up a model class based on the regex parameter "model" (or from the GET data), which is a
    valid ``ContentType`` pk.

    """

    def get(self, request, *args, **kwargs):
        data = {'choices': self.configuration.get_searchable_field_choices(include_types=True)}

        return HttpResponse(json.dumps(data, indent=4), content_type='text/json')

class ConstraintOperatorsAjaxView(BaseAjaxConfigurationResolutionView):
    """
    Looks up a model class based on the regex parameter "model" (or from the GET data), which is a
    valid ``ContentType`` pk.

    """

    def get(self, request, *args, **kwargs):
        field = request.GET.get('field')

        try:
            choices = self.configuration.get_operator_choices(hash=field, flat=True)
        except AttributeError:
            choices = None

        if not choices:
            return HttpResponseBadRequest("Bad field")

        data = {'choices': choices}

        return HttpResponse(json.dumps(data, indent=4), content_type='text/json')


