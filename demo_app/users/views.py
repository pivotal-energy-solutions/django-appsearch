# -*- coding: utf-8 -*-
"""views.py.py: """

from __future__ import absolute_import, print_function, unicode_literals

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic.edit import UpdateView


__author__ = 'Artem Hruzd'
__date__ = '08/07/2019 21:59'
__copyright__ = 'Copyright 2011-2019 Pivotal Energy Solutions. All rights reserved.'
__credits__ = ['Artem Hruzd', 'Steven Klass', ]


User = get_user_model()
