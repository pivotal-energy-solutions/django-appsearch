# -*- coding: utf-8 -*-
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Axis-customized User model."""

    company = models.ForeignKey(
        "company.Company", related_name="users", blank=True, null=True, on_delete=models.SET_NULL
    )

    title = models.CharField(max_length=32, null=True, blank=True)
    department = models.CharField(max_length=16, blank=True)
    work_phone = models.CharField(max_length=16, blank=True, null=True)
    cell_phone = models.CharField(max_length=16, blank=True, null=True)

    is_company_admin = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    last_update = models.DateTimeField(auto_now=True, blank=True, null=True)
