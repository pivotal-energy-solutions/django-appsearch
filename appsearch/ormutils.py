# -*- coding: utf-8 -*-
"""ormutils.py: ORM Utils"""

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

try:
    from django.db.models.sql.constants import LOOKUP_SEP
except:
    from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields import FieldDoesNotExist

def resolve_orm_path(model, orm_path):
    """
    Follows the queryset-style query path of ``orm_path`` starting from ``model`` class.  If the
    path ends up referring to a bad field name, ``django.db.models.fields.FieldDoesNotExist`` will
    be raised.

    """

    bits = orm_path.split(LOOKUP_SEP)
    endpoint_model = reduce(get_model_at_related_field, [model] + bits[:-1])
    field = endpoint_model._meta.get_field(bits[-1])
    return field


def get_model_at_related_field(model, attr):
    """
    Looks up ``attr`` as a field of ``model`` and returns the related model class.  If ``attr`` is
    not a relationship field, ``ValueError`` is raised.

    """

    try:
        field = model._meta.get_field(attr)
    except FieldDoesNotExist:
        raise

    if not field.concrete:
        if hasattr(field, 'related_model'):  # Reverse relationship
            return field.related_model

    if hasattr(field, 'remote_field') and field.remote_field:  # Forward/m2m relationship
        rel = getattr(field, 'remote_field', None)
        return rel.model

    raise ValueError("{0}.{1} ({2}) is not a relationship field.".format(model.__name__, attr, field.__class__.__name__))
