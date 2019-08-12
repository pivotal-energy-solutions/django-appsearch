# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import User


class UserAdminCreationForm(UserCreationForm):

    class Meta:
        model = get_user_model()
        fields = '__all__'

    def clean_username(self):
        """This has to be over written to use Axis' declared Auth Model."""
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147
        username = self.cleaned_data['username']
        UserModel = get_user_model()
        try:
            UserModel._default_manager.get(username=username)
        except UserModel.DoesNotExist:
            return username
        raise ValidationError(
            self.error_messages['duplicate_username'],
            code='duplicate_username',
        )


class UserAdminChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'
