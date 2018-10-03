# -*- coding: utf-8 -*-
"""views.py: ORM Utils"""

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

from django.views.generic import TemplateView

from appsearch.utils import Searcher


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


