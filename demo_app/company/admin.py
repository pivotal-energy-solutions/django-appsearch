# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Company


class CompanyAdmin(admin.ModelAdmin):
    """
    Company admin panel
    """

    list_display = ("name",)


admin.site.register(Company, CompanyAdmin)
