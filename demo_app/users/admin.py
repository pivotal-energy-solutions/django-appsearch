from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm, UserAdminCreationForm
from .models import User


class UserAdmin(AuthUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    fieldsets = (
        (
            None,
            {
                "fields": ("username", "password"),
            },
        ),
        (
            _("User Profile"),
            {
                "fields": ("first_name", "last_name", "email"),
            },
        ),
        (
            _("Company Info"),
            {
                "fields": (
                    "company",
                    "title",
                    "department",
                    "work_phone",
                    "cell_phone",
                    "date_joined",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_public",
                    "is_company_admin",
                    "is_superuser",
                ),
            },
        ),
    )


admin.site.register(User, UserAdmin)
