# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import logging
from operator import itemgetter, attrgetter
from collections import OrderedDict
from itertools import chain
try:
   from hashlib import sha1 as sha
except ImportError:
    from sha import sha

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.constants import LOOKUP_SEP
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.utils.text import capfirst
from django.forms.forms import pretty_name

from .ormutils import resolve_orm_path


log = logging.getLogger(__name__)

# Base fields to detect built-in operator types.  Fields that subclass these are implicitly included
# in the type check.
TEXT_FIELDS = (models.CharField, models.TextField, models.FilePathField, models.IPAddressField,
               models.GenericIPAddressField, models.FileField)
DATE_FIELDS = (models.DateField, models.TimeField)
NUMERIC_FIELDS = (models.IntegerField, models.AutoField, models.FloatField, models.DecimalField)
BOOLEAN_FIELDS = (models.BooleanField, models.NullBooleanField)
RELATIONSHIP_FIELDS = (models.ForeignKey, models.ManyToManyField, models.OneToOneField)

# Maps the core field types to the default available search operators.
# The ORM query representation (e.g., "icontains") is not sent to the frontend.
# Notably, entries starting with  "!" are negative filters
OPERATOR_MAP = {
    'text': (
        ('icontains', "contains"),
        ('!icontains', "doesn't contain"),
        ('iexact', "= equal"),
        ('!iexact', "≠ not equal"),
        ('!isnull', "exists"),
        ('isnull', "doesn't exist"),
    ),
    'date': (
        ('exact', "= equal"),
        ('!exact', "≠ not equal"),
        ('gt', "> greater than"),
        ('lt', "< less than"),
        ('range', "between"),
        ('!isnull', "exists"),
        ('isnull', "doesn't exist"),
    ),
    'number': (
        ('exact', "= equal"),
        ('gt', "> greater than"),
        ('lt', "< less than"),
        ('range', "between"),
        ('!isnull', "exists"),
        ('isnull', "doesn't exist"),
        ('icontains', "contains"),
        ('!icontains', "doesn't contain"),
    ),
    'boolean': (
        ('exact', "= equal"),
        ('!isnull', "exists"),
        ('isnull', "doesn't exist"),
    ),
    'model': (
        ('!isnull', "exists"),
        ('isnull', "doesn't exist"),
    ),

    # If a field defines a "choices" list, we can't get very fancy with operator types
    'choices': (
        ('exact', "is"),
    ),
}


class ModelSearch(object):
    """ Contains search and display configuration for a single Model. """

    model = None
    verbose_name = None
    verbose_name_plural = None

    display_fields = None
    search_fields = None

    _display_fields = None
    _fields = None

    def __init__(self, model):
        self.model = model
        if not self.verbose_name_plural:
            # If the plural name is unset, but the single name is, pluralize the single name instead
            # of reverting back to the model's Meta verbose_plural_name (which might just be a
            # pluralization of its verbose_name, which is explicitly being overridden).
            if self.verbose_name:
                self.verbose_name_plural = self.verbose_name + "s"
            else:
                self.verbose_name_plural = capfirst(self.model._meta.verbose_name_plural)
        if not self.verbose_name:
            self.verbose_name = capfirst(self.model._meta.verbose_name)

        # Read the configured fields
        self._process_display_fields()
        self._process_searchable_fields()

        # Determine the ContentType in advance.
        self._content_type = ContentType.objects.get_for_model(self.model)

        # Process the display fields
        if not self.display_fields:
            self.display_fields = list(map(attrgetter('name'), self.model._meta.local_fields))

    def _process_display_fields(self):
        """
        Converts a potentially uneven collection of strings and tuples in ``display_fields`` to
        a uniform list of 3-tuples in the form ("Verbose name", "field_name", field_instance)

        """

        self._display_fields = []
        for field_info in self.display_fields:
            if isinstance(field_info, (tuple, list)):
                verbose_name, field_name = field_info
            else:
                field_name = field_info
                verbose_name = None

            field = resolve_orm_path(self.model, field_name)

            if verbose_name is None:
                verbose_name = field.verbose_name

            self._display_fields.append((capfirst(verbose_name), field_name, field))
        return self._display_fields

    def _process_searchable_fields(self):
        """
        Crunches the information in ``display_fields`` and the intricate ``search_fields`` to
        produce a single consistent index of all searchable fields.

        The resulting index is formatted as an OrderedDict where keys are "friendly" readable names
        and are mapped to ORM-style paths such as "subdivision__name"

        """

        self._fields = OrderedDict()

        # Get flattened sequence of 3-tuples: ([orm_path,...], verbose_name, Field)
        extended_info = self._get_field_info([], self.model, None, self.search_fields)

        # Store each element's [:2] as the field choices
        self._fields.update(map(itemgetter(slice(2)), extended_info))

        # Store each element's [::2] (that is, [0] and [2]) as a mapping to the field object
        self.field_types = dict(map(itemgetter(slice(0, None, 2)), extended_info))




    def _get_field_info(self, orm_path_bits, model, related_name, field_list,
                        include_model_in_verbose_name=True):
        """
        Recurses the fields listed on the model to provide a complete index of their ORM paths and
        friendly names.
        """

        if related_name:
            if isinstance(related_name, basestring):

                try:
                    # Post 1.8
                    field = model._meta.get_field(related_name)
                    direct = not field.auto_created or field.concrete
                    related_model = None if field.model._meta.concrete_model is model else field.model._meta.concrete_model
                except FieldDoesNotExist:
                    # Pre 1.8
                    field, related_model, direct, m2m = model._meta.get_field_by_name(related_name)

                if related_model is None:  # Field is local, follow relationship to find the model
                    if direct:
                        if hasattr(field, 'field'):
                            related_model = field.field.remote_field.model
                        else:
                            related_model = field.remote_field.model
                    else:

                        if hasattr(field, 'related_model'):
                            # Post 1.8
                            related_model = field.related_model
                        else:
                            # Pre 1.8
                            related_model = field.model
                else:  # Field is a virtual field from reverse relation
                    if hasattr(field, 'related_model'):
                        # Post 1.8
                        related_model = field.related_model
                    else:
                        # Pre 1.8
                        related_model = field.model
            else:
                # Syntax allowing a model class reference itself.
                # Trace the relationship backwards from the related class's Meta to get the field
                # name.
                related_model = related_name

                try:
                    # Post 1.8
                    fk_objects = [
                        f for f in related_model._meta.get_fields()
                        if (f.one_to_many or f.one_to_one)
                           and f.auto_created and not f.concrete
                    ]
                    m2m_objects = [
                        f for f in related_model._meta.get_fields(include_hidden=True)
                        if f.many_to_many and f.auto_created
                    ]

                except:
                    # Pre 1.8
                    raise
                    fk_objects = related_model._meta.get_all_related_objects()
                    m2m_objects = related_model._meta.get_all_related_many_to_many_objects()

                for related_object in chain(fk_objects, m2m_objects):
                    if related_object.field.model is model:
                        related_name = related_object.field.name
                        break
                else:
                    raise ValueError("Relationship field from %r to %r not found." % (
                        model.__name__, related_model.__name__))
        else:
            related_model = model


        base_orm_path = orm_path_bits
        sub_fields = []

        for field_name in field_list:
            if isinstance(field_name, dict):
                # Nested dict.  Recurse the function with the new related context
                extended_name, sub_field_list = field_name.items()[0]
                orm_path_bits = base_orm_path[:]
                if related_name:
                    orm_path_bits.append(related_name)
                sub_fields.extend(self._get_field_info(orm_path_bits, related_model, extended_name,
                        sub_field_list))
            else:
                # Raw field name or 2-tuple

                field = None
                # Check for a 2-tuple of ("Friendly name", "field_name")
                if isinstance(field_name, (tuple, list)):
                    verbose_name, field_name = field_name
                else:
                    # Derive a verbose name.  If the field comes from a model other than the base
                    # model, prepend the relate model's own verbose name.
                    try:
                        # Post 1.8
                        field = related_model._meta.get_field(field_name)
                    except:
                        # Pre 1.8
                        field, _, _, _ = related_model._meta.get_field_by_name(field_name)

                    if related_name:
                        verbose_name_bits = [related_model._meta.verbose_name, field.verbose_name]
                    else:
                        verbose_name_bits = [field.verbose_name]
                    verbose_name = ' '.join(map(pretty_name, verbose_name_bits))

                if not isinstance(field_name, (tuple, list)):
                    field_name = (field_name,)
                if field is None:
                    field = resolve_orm_path(related_model, field_name[0])

                try:
                    field = field.field
                except:
                    pass

                orm_path_bits = base_orm_path[:]
                if related_name:
                    orm_path_bits.append(related_name)

                orm_info = tuple('__'.join(orm_path_bits + [component])
                        for component in field_name)
                sub_fields.append([orm_info, verbose_name, field])
                # print orm_info, field.name, related_model, verbose_name

            # print sub_fields

        return sub_fields

    def get_operator_choices(self, field=None, hash=None, flat=False):
        """
        Returns the sequence of 2-tuples of ('querytype', "Friendly Operator Name") for the given
        ``field`` Field instance, or given the ``hash`` representing that field.

        If ``flat``, then only the text from each option is returned (read: not the "value"),
        forming a sequence of strings such as ("= equal", "< less than", ...).

        """

        # TODO: Fields with a "choices" setting might be an IntegerField, but provide text-based
        # values that the user will intuitively use as search values.  A "choices" setting might
        # need to assume string data regardless of the underlying type.

        if hash is not None:
            field = self.reverse_field_hash(hash)
        elif field is None:
            return []

        field_type = self.field_types[field]
        classification = self.get_field_classification(field_type)
        choices = OPERATOR_MAP[classification]

        # Remove the 'isnull' and 'isnotnull' operators if this field instance can't be null anyway
        if not field_type.null:
            choices = filter(lambda c: c[0] not in ('isnull', '!isnull'), choices)

        if flat:
            choices = map(itemgetter(1), choices)

        return choices

    def get_field_classification(self, field):
        """
        Use field (either a proper Django ``Field`` instance or a field definition tuple from the
        configuration) to return a type label for the field's data type.

        Returns one of "text", "date", "number", "boolean", or "model" (for relationship fields).

        """

        if isinstance(field, tuple):
            field = self.field_types[field]

        if field.choices:
            return 'choices'
        elif isinstance(field, TEXT_FIELDS):
            return 'text'
        elif isinstance(field, DATE_FIELDS):
            return 'date'
        elif isinstance(field, NUMERIC_FIELDS):
            return 'number'
        elif isinstance(field, BOOLEAN_FIELDS):
            return 'boolean'
        elif isinstance(field, RELATIONSHIP_FIELDS):
            return 'model'
        else:
            raise ValueError("Unhandled field type %s" % field.__class__.__name__)

    def get_searchable_field_choices(self, include_types=False):
        """
        Returns an iterable of 2-tuples suitable for use as a form's ``choices`` attribute.

        The ORM path is obscured for use as the <option> tag values.

        """

        choices = self._fields.items()
        if include_types:
            choices = map(lambda c: c + (self.get_field_classification(c[0]),), choices)

        # Perform a sha hash on the ORM path to get something unique and obscured for the frontend
        encode_value = lambda pair: (sha(','.join(pair[0])).hexdigest(),) + tuple(pair[1:])
        return map(encode_value, choices)

    def reverse_field_hash(self, hash):
        """ Returns the hash of field ORM paths derived from the initial configuration. """

        hashes = map(itemgetter(0), self.get_searchable_field_choices())
        try:
            return self._fields.keys()[hashes.index(hash)]
        except IndexError:
            # raise ValueError("Unknown field hash")
            # TODO Fix me!
            log.exception("Unknown field hash")
            return None

    def get_display_fields(self):
        """ Returns the list of labels for the display fields. """
        return list(map(itemgetter(0), self._display_fields))

    def user_has_perm(self, user):
        """
        Returns ``True`` or ``False`` to indicate definitive user permission, or else ``None`` to
        let the registry default permission decide.

        """

        return None

    def get_queryset(self, request, user):
        """
        Hook for subclasses to modify querysets.  By default, this method returns the default
        manager's ``.all()`` method.  The request and user are also available for special
        requirements.

        """
        return self.model.objects.all()

    def get_object_data(self, obj):
        """
        Returns a list of values retrieved from ``obj``, automatically fetched according to the
        configured ``display_fields``.  Values that raise ``ObjectDoesNotExist`` or cause
        ``AttributeError`` (such as a null ForeignKey in the middle of a chain lookup) are
        suppressed and replaced with ``None``.

        """

        data = []
        for _, field_name, _ in self._display_fields:
            try:
                value = reduce(getattr, [obj] + field_name.split(LOOKUP_SEP))
            except (ObjectDoesNotExist, AttributeError):
                value = None

            if callable(value):
                value = value()
            data.append(value)

        # Convert the first column's data into a link to the model instance
        if hasattr(obj, 'get_absolute_url'):
            data[0] = "<a href='{}'>{}</a>".format(obj.get_absolute_url(), data[0])

        return data

class SearchRegistry(object):
    """
    Holds the gathered configurations from apps that use an appsearch.py module.

    """

    _registry = None
    permission = 'change_{}'

    def __init__(self):
        self._registry = {}

    def __iter__(self):
        for k in self._registry:
            yield k

    def __getitem__(self, k):
        if not isinstance(k, basestring):
            k = '.'.join((k._meta.app_label, k.__name__.lower()))
        return self._registry[k]

    def __contains__(self, k):
        try:
            config = self.__getitem__(k)
            return True
        except KeyError:
            return False

    def register(self, model, configuration):
        id_string = '.'.join((model._meta.app_label, model.__name__)).lower()
        log.debug("Registering %r for appsearch configuration class %r", id_string, configuration)
        self._registry[id_string] = configuration(model)

    def filter_configurations_by_permission(self, user, permission_code):
        configurations = self._registry.values()
        if permission_code is None:
            permission_code = self.permission

        def check_permission(config):
            permission = permission_code.format(config.model.__name__.lower())
            permission = '{}.{}'.format(config.model._meta.app_label, permission)
            return user.has_perm(permission)

        if user:
            configurations = filter(check_permission, configurations)

        return configurations

    def sort_function(self, configurations):
        return sorted(configurations, key=attrgetter('verbose_name'))

    def set_sort_function(self, f):
        self.sort_function = f

    def sort_configurations(self, configurations):
        return self.sort_function(configurations)

    def get_configurations(self, user=None, permission=None):
        """
        Hook for returning the registry data in a particular order.  By default, the configurations
        are returned in alphabetical order according to their model names.

        """

        configurations = self.filter_configurations_by_permission(user, permission)

        return self.sort_configurations(configurations)

    def get_configuration(self, model, user=None, permission=None):
        try:
            configuration = self[model]
        except KeyError:
            log.warn("No registered configuration for model %r.", model)
            configuration = None
        else:
            if user:
                available_configurations = self.filter_configurations_by_permission(user, permission)
                if configuration not in available_configurations:
                    log.warn("Configuration for model %r available, but user %r doesn't have "
                            "permission (permission filter: %r).", model, user.username,
                            permission or self.permission)
                    configuration = None

        return configuration

search = SearchRegistry()
