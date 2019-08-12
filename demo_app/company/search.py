# -*- coding: utf-8 -*-
"""search.py: Django company"""

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

from appsearch.registry import ModelSearch, search
from .models import Company

__author__ = 'Steven Klass'
__date__ = '08/07/2019 21:59'
__copyright__ = 'Copyright 2011-2019 Pivotal Energy Solutions. All rights reserved.'
__credits__ = ['Artem Hruzd', 'Steven Klass', ]


class CompanySearch(ModelSearch):
    display_fields = (
        'name',
        'slug',
        'company_type'
    )

    search_fields = (
        'name',
        'company_type'
    )

search.register(Company, CompanySearch)
