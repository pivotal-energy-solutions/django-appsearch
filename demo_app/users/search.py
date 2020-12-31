# -*- coding: utf-8 -*-
"""search.py: Django """

from __future__ import absolute_import, print_function, unicode_literals

import logging

from django.contrib.auth import get_user_model

from appsearch.registry import ModelSearch, search


__author__ = 'Steven Klass'
__date__ = '08/07/2019 21:59'
__copyright__ = 'Copyright 2011-2020 Pivotal Energy Solutions. All rights reserved.'
__credits__ = ['Artem Hruzd', 'Steven Klass', ]

log = logging.getLogger(__name__)

User = get_user_model()


class UserSearch(ModelSearch):
    display_fields = (
        ('First', 'first_name'),
        ('Last', 'last_name'),
        ('Email', 'email'),
        ('Work Phone', 'work_phone'),
        ('Company', 'company__name'),
        ('Active', 'is_active'),
    )

    search_fields = (
        ('First', 'first_name'),
        ('Last', 'last_name'),
        ('Email', 'email'),
        {'company': (
            ('Company Name', 'name'),
            ('Company Type', 'company_type'),
        )},
        ('Is Active', 'is_active'),
    )


search.register(User, UserSearch)
