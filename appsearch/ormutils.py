# -*- coding: utf-8 -*-
"""ormutils.py: ORM Utils"""

from __future__ import unicode_literals

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
    field, _, _, _ = endpoint_model._meta.get_field_by_name(bits[-1])
    return field


def get_model_at_related_field(model, attr):
    """
    Looks up ``attr`` as a field of ``model`` and returns the related model class.  If ``attr`` is
    not a relationship field, ``ValueError`` is raised.

    """

    try:
        field, _, direct, m2m = model._meta.get_field_by_name(attr)
    except FieldDoesNotExist:
        raise

    if not direct and hasattr(field, 'model'):  # Reverse relationship
        model = field.model
    elif hasattr(field, 'rel') and field.rel:  # Forward/m2m relationship
        model = field.rel.to
    else:
        raise ValueError("{0}.{1} ({2}) is not a relationship field.".format(model.__name__, attr,
                field.__class__.__name__))
    return model


