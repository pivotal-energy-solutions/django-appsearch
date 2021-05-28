# -*- coding: utf-8 -*-
from django.db import models


class Company(models.Model):
    BUILDER_COMPANY_TYPE = "builder"
    RATER_COMPANY_TYPE = "rater"
    PROVIDER_COMPANY_TYPE = "provider"

    COMPANY_TYPE_CHOICES = (
        (BUILDER_COMPANY_TYPE, "Builder"),
        (RATER_COMPANY_TYPE, "Rater"),
        (PROVIDER_COMPANY_TYPE, "Provider"),
    )

    name = models.CharField(max_length=25)
    company_type = models.CharField(max_length=100, choices=COMPANY_TYPE_CHOICES)

    home_page = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    default_email = models.EmailField(blank=True, null=True)

    slug = models.SlugField("slug", unique=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name
