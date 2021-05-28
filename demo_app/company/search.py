# -*- coding: utf-8 -*-
"""search.py: Django company"""


from appsearch.registry import ModelSearch, search

from .models import Company


__author__ = "Steven Klass"
__date__ = "08/07/2019 21:59"
__copyright__ = "Copyright 2011-2020 Pivotal Energy Solutions. All rights reserved."
__credits__ = [
    "Artem Hruzd",
    "Steven Klass",
]


class CompanySearch(ModelSearch):
    """
    Company search available for all users
    """

    display_fields = ("name", "slug", "company_type")

    search_fields = ("name", "company_type")

    def user_has_perm(self, user):
        return True


search.register(Company, CompanySearch)
