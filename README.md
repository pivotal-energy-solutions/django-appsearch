# django-appsearch

Framework and generic app for cross-model searches on a single page

Major sections:

* [Usage](#usage)
* [API](#api)

## Authors

* Tim Valenta
* Gaurav Kapoor
* Steven Klass

## Usage

Appsearch integration is composed of a few separate parts.  In the simplest default setup, you must at least do the following:

* Register models with appsearch
* Call `appsearch.autodiscover()` (probably somewhere in your project's urls, like the similar admin function)
* Create your main view where the search page should appear
* Create a simple template where the search form can be rendered

There are ways to customize the templates, modify the search queryset, etc, which is covered after the basic introduction.

### Model registration


Patterned after `django.contrib.admin` interface, appsearch includes a `registry` submodule, which contains a `ModelSearch` class (along the lines of the admin's `ModelAdmin`), and a default registry object called `search`.

`ModelSearch` has a few basic options, the most important of which are `search_fields` and `display_fields`.

We'll use this example base model for registration, which reaches out to a couple of other fake models for the sake of demonstration:

```python
# car/models.py

class Car(models.Model):
    year = models.PositiveIntegerField()
    make = models.ForeignKey(CarMake)
    model = models.ForeignKey(CarModel)

    owners = models.ManyToManyField(User)

    nickname = models.CharField(max_length=50)
    adoption_story = models.TextField()
```

##### `search_fields`

To register this model, place a `search.py` submodule in your app's directory and include at least this basic registration code.  We'll leave out the majority of `Car`'s fields for clarity:

```python
# car/search.py

from appsearch.registry import ModelSearch, search
from project.car.models import Car

class CarSearch(ModelSearch):
    search_fields = (
        'year',
        'nickname',
        'adoption_story',
    )

search.register(Car, CarSearch)
```

`search_fields` is an iterable whose items describe searchable fields.  The order that the fields are listed here will be respected in the appsearch UI.  An item in the list can be a string if it directly describes a model field name.  The field will be looked up and its `verbose_name` stored for use in the UI.  To explicitly declare a "verbose name" for use within the appsearch UI, you can make the string a 2-tuple of the verbose name and the field name:

```python
search_fields = (
    'year',
    ("Name", 'nickname'),
    'adoption_story',
)
```

To pull related fields into the mix, an item can instead be a single-entry dictionary, mapping the attribute to a nested structure following the same format:

```python
search_fields = (
    'year',
    ("Name", 'nickname'),
    'adoption_story',
    {'make': (
        'name',
    )},
    {'model': (
        'name',
    )},
    {'owners': (
        'username',
        'first_name',
        'last_name',
    )},
)
```

This syntax reduces potentially repetitive query language such as `"owners__username"`, `"owners__first_name"`, and `"owners__last_name"`.

Any related field that doesn't supply its own verbose name here in the search configuration will be displayed with the related model's `verbose_name` in front of it.  In other words, to prevent the search UI from presenting an owner's `"first_name"` field as if it were the car's first name, the UI will prefix the field's name with the `User` model's verbose_name.  In this example, `first_name` would be shown as "User first name".

To prevent the automatic prefix, you can supply your own verbose name as previously shown:

```python
search_fields = (
    # ...
    {'owners': (
        ("Username", 'username'), # would have been "User username"
        ("User's First name", "first_name"), # would have been "User first name"
        ("User's Last name", "last_name"), # would have been "User last name"
    )},
)
```

Related fields can be nested:

```python
search_fields = (
    # ...
    {'owners': (
        'username', # displayed as "User username"
        {'groups': (
            'name', # displayed as "Group name"
        )},
    )},
)
```

Another way to specify a related field is to use the related model class itself as the dictionary key.  Using this method, the field name will automatically be retrieved by inspecting the relationships between the two models:

```python
    search_fields = (
        # ...
        {User: ( # validated to the string "owner", as in the previous example
            'username', # displayed as "User username"
            {'groups': (
                'name', # displayed as "Group name"
            )},
        )}
    )
```

Eventually this syntax will be the supported method for accessing generic foreign keys, although such relationships are not yet implemented.

**NOTE**: Generic models that are referenced by a [GenericRelation](https://docs.djangoproject.com/en/dev/ref/contrib/contenttypes/#reverse-generic-relations) field (e.g., a Car object with a GenericRelation field called "comments" to a generic Comment model) are considered valid and are digested by the appsearch framework:

```python
search_fields = (
    # ...
    {'comments': ( # Car.comments as a GenericRelation field to Comment model
        'title',
        'content',
    )},
)
```

##### `display_fields`

By default, the results table shown by appsearch will include all local fields on the model.  To explicitly declare the field list, your configuration can include another attribute `display_fields`, which follows a similar format to `search_fields`:

```python
class CarSearch(ModelSearch):
    display_fields = (
        'nickname',
        'year',
        ("Make", 'make__name'),
        ("Model", 'model__name'),
        ("Owners", 'get_owners_list'), # attribute on the Car model
    )

    search_fields = (
        # ...
    )
```

`display_fields` is an iterable of items, either strings or 2-tuples of (verbosename, fieldname).  As with `search_fields`, fields will have their `verbose_name` automatically retrieved, unless it is supplied explicitly in the configuration.

A field isn't necessarily required to be a database field; in the example above, we've placed an "Owners" column in the table headers, and the field is actually a method name.  This is convenient, but be careful not generate too many queries outside of appsearch's control!

The first item in this list will be converted into a link, wrapping the value with a simple snippet of HTML: `<a href="{{ object.get_absolute_url }}">{{ value }}</a>`

appsearch will examine `display_fields` to discover how to best issue a `select_related()` call to the search results queryset, which helps keep the automatic query count low.

### `appsearch.autodiscover()`

As with the built-in admin, appsearch can crawl your apps to discover a `search.py` module in each one.  `autodiscover()` doesn't do anything but import those configurations and cause them to execute, so if you're using custom or multiple registries, this function will let those registries set themselves up.

As with the admin, a nice place to call `autodiscover()` is in your urls module, either at the root of your project or in a local "search" app where you are going to set up the view anyway.  See the example in the next section.

### The main view

You need to declare your own starting point for the client to initially visit and configure a search.

`BaseSearchView` is a simple `TemplateView` subclass that also inherits from `appsearch.views.SearchMixin`.  For a completely vanilla behavior, you could include the `BaseSearchView` directly:

```python
# project/mysearchapp/urls.py

from django.conf.urls.defaults import patterns, url
from appsearch.views import BaseSearchView
import appsearch.autodiscover

appsearch.autodiscover()

urlpatterns = patterns('',
    url(r'^search/$', BaseSearchView.as_view(template_name="search.html")),
)
```

Remember, because `BaseSearchView` is pretty much just a `TemplateView`, you need to give it a `template_name` value.  Don't worry though, since the view inherits machinery for making the search form trivial to render into your custom template.

Alternately, you can of course go and actually subclass `BaseSearchView` and gain access to extra flexibility:

```python
# project/mysearchapp/views.py

from appsearch.views import BaseSearchView

class SearchView(BaseSearchView):
    template_name = "search.html"
```

#### search.html

You're free to make whatever template you want for the search to exist on.  By default, all you need to do is render the ``search`` context variable into your template.  Just make sure that jQuery and the appsearch plugin are loaded:

```html
{# search.html #}

{% block javascript %}
    <script type="text/javascript" src="{{ STATIC_URL }}js/jquery-1.8.3.min.js"></script>
    <script type="text/javascript" src="{{ STATIC_URL }}js/jquery.appsearch.js"></script>
{% endblock %}

{% block content %}
    {{ search }}
{% endblock %}
```

There are plenty of ways to customize how the form is rendered and how the Javascript behaves, but this is enough to get a fully functioning search implementation.

### That's it!

With the ajax urls mounted, your instance of `BaseSearchView` in play, and your model configurations registered, and your template dumping out the generated form, you're finished.

## API

* [ModelSearch](#modelsearch)
* [SearchRegistry](#searchregistry)

### `ModelSearch`
**`appsearch.registry.ModelSearch`**

The base configuration class used to register a model for search discovery.

#### `verbose_name`
If provided, the model that is registered with this ModelSearch instance will take on this verbose name, hiding the model's own `verbose_name` option.

**Default**: The registered model's `verbose_name`

#### `verbose_name_plural`
If provided, the model that is registered with this ModelSearch instance will take on this plural verbose name, hiding the model's own `verbose_name` option.

**Default**: The plural of the configuration's `verbose_name`, if available, or else the model class's `verbose_name_plural`.

#### `display_fields`
An iterable of column description items.

Each "item" can be a string:

```python
'field_name'
```

or a 2-tuple where the verbose name is explicitly supplied:

```python
("My field name", 'field_name')
```

In either case, the field name can refer to a local field (including a method name), or a queryset-style lookup path.  In the latter case, an explicit verbose name should be supplied:

```python
("Related field name", 'relationship__field_name')
```

Any cross-model lookups will be automatically detected and the appropriate `.select_related()` statement will be issued.

**Default**: All local fields

#### `search_fields`

An iterable of field description items.

Each "item" can be a string describing a local database field:

```python
'field_name'
```

or a 2-tuple where the verbose name is explicitly supplied:

```python
("My field name", 'field_name')
```

or a single-item dictionary mapping a related accessor to a new iterable of related field description items following the same format rules:

```python
{'users': (
    # strings, 2-tuples, or more nested single-item dictionaries
)}
```

The order in which `search_fields` are declared will be respected by the search form UI.

For related fields inside of a dictionary item, verbose names will be prefixed with the field's model's `verbose_name`:

```python
{'users': (
    'username', # displays User's verbose name + User.username's verbose name: "User username"
)}
```

The prefix will not be added if the field already explicitly declares a verbose name:

```python
{'users': (
    ("Username", 'username'), # displays "Username" only
)}
```

#### `get_queryset(user)`

Returns the base queryset that searches on this model will use to apply the generated query.  By default the model's default manager is used to return an unfiltered queryset.  An appropriate use of this hook would be to use a different manager, or to limit the queryset based on a permission mechanism.

`user` is the user issuing the request.

#### `get_object_data(obj)`
Given a search result object `obj`, return a list of data fields for the frontend table.  The length of the list should match the number of display columns.

The default implementation will automatically read the attributes specified in the configuration's `display_fields` and build this list.  If a value is callable, it will be called with no arguments and the return value used in its place, allowing `display_fields` to specify instance attributes and methods, along with concrete database-backed fields.

The work done by the default search mechanism will attempt to call `select_related()` on the source queryset before this method is called on each result object, but be careful not to generate excessive queries per object.  If additional related fields need to be selected to avoid high query counts, you can supply your own subclass of [`Searcher`](#searcher) and either:

1. Override `Searcher.build_queryset()` method, calling super() and performing extra `select_related()` calls on the return value.
2. Override `get_select_related_fields()` directly and adding to the list.

### `SearchRegistry`
**`appsearch.registry.SearchRegistry`**

The registry container where configurations are stored for use in the search form.

The default registry is made available in the module variable called `search`.

#### `__iter__()`
Yields the registration keys, which are strings in the form `"applabel.modelname"`.

#### `__getitem__(k)`
If `k` is a model class, the registration key is generated (`"applabel.modelname"`) in its place.  Otherwise, `k` is directly used to look up a model configuration in the registry.

#### `__contains__(k)`
If `k` is a model class, the registration key is generated (`"applabel.modelname"`) in its place.  Otherwise, `k` is directly used to test membership in the registry.

#### `register(model, configuration)`
Registers a model class `model` with the given `configuration` class.

#### `get_configuration(model)`
Returns the configuration instance associated with `model`.

#### `get_configurations([user[, permission]])`
Returns the configurations in sorted order.

If `user` is specified, configurations will be included only if the user has the built-in `"applabel.change_modelname"` permission on the associated model class.

If `permission` is also supplied, it should be a string with two string-formatting positions for the applabel and the modelname, such as `"{}.add_{}"` or `{}.manage_{}`.

#### `set_sort_function(f)`
`f` should be a function that accepts a parameter `configurations` and returns the configurations in the desired order.  The default sort function arranges the configurations based on their `verbose_name` attributes.

### `Searcher`
**`appsearch.utils.Searcher`**

The object wrapping all data necessary to render the search UI and execute the search itself.  The current instance is sent to the form template context, by default with the name `"search"`.

The `Searcher` class can be specified by the instance of the `BaseSearchView` producing the main search page.

#### `form_template_name`
**Default**: `"appsearch/default_form.html"`

Normally the view that builds the `Searcher` instance will supply its own template name, but in the event that the view's value is explicitly set to `None`, or the `Searcher` is being custom constructed, this value will be used.

#### `search_form_template_name`
**Default**: `"appsearch/search_form.html"`

Same as `form_template_name`.

#### `results_list_template_name`
**Default**: `"appsearch/results_list.html"`

Same as `form_template_name`.

#### `__unicode__()`

Renders the template name at `self.form_template_name`.

This default template automatically calls `render_search_form()` and `render_results_list()`, making it the simplest way to generate the appsearch UI.

#### `render_search_form()`

Renders the template name at `self.search_form_template_name`.

This generates the HTML for the forms, not including the results list.

#### `render_results_list()`

Renders the template name at `self.results_list_template_name`.

This generates the HTML for the results list, not including the forms.  This result is empty if the search was not executed during the current request.

#### `model_selection_form`
An instance of `appsearch.forms.ModelSelectionForm`.

#### `constraint_formset`
An instance of `appsearch.forms.ConstraintFormset`, containing `appsearch.forms.ConstraintForm` instances.

#### `field_data_url`
The URL the appsearch Javascript should use to fetch the list of searchable fields for a given model once a selection has been made on `model_selection_form`.  The URL is derived at construction time by reversing the default URL name `"appsearch:constraint-fields"`, optionally including the prefix designated at construction time, sent in by the view building the Searcher out of the keyword arguments returned by `BaseSearchView.get_searcher_kwargs()`.

#### `operator_data_url`
Like `field_data_url`, the URL the appsearch Javascript should use to fetch the list of valid operators for the model and field combination selected on the UI.

#### `ready`
A read-only flag for determining if a search can be performed.  `ready` is only True if both the model selection form and the constraint formset pass the normal `is_valid()` checks.

#### `model`
Only available after `ready` is checked and `model_selection_form` can have its selected model determined.  The model class that the search will operator on.

#### `model_config`
Only available after `ready` is checked, like `model`.  The configuration `ModelSearch` instance associated with the selected model class.

#### `results`
A dictionary of result data available after `ready` is True and the view had consequently generated the final search query and executed it.  The `results` dictionary is used exclusively in the templates to render the UI table with the column headers and row data.

##### `results['count']`
The length of the result queryset.

##### `results['list']`
The iterable list of data rows.  Each "row" is represented by a list of column data for the UI table.  The results list is made up of the return values of `ModelSearch.get_object_data()`.

##### `results['fields']`
The list of verbose names to represent the fields designated by the model's `ModelSearch.display_fields` list.

##### `results['natural_string']`
A string built using the constraint formset options, built with a prefix string "where" and joining each constraint form with a comma.  The result is a string in the format:

    "where {verbosename1} {operator1} {value1}, {verbosename2} {operator2} {value2}"

#### `build_queryset(model, query[, queryset=None])`
When the forms are valid and the search will be performed, this method applies the `query` object (a combination of `django.db.models.query.Q` instances) to the `model` class.  This method takes care to also select the necessary related fields that the model configuration will show via `ModelSearch.display_fields`.

This can serve as a hook for the Searcher object to make final modifications to the query, regardless of the model class.  Most queryset modifications should take place in each `ModelSearch.get_queryset()` method, since each model can control its base queryset in a clearer context.

By default, the machinery in appsearch will not pass a `queryset` argument directly to this method, but if you subclass `Searcher` and override this method, you may call `super()` to send this default implementation a base queryset to use in place of the model's default manager queryset.  This is appropriate when all searchable models use a common query interface, such as sharing a project-level object manager or permission system.

The return value of this method is the queryset resulting from the model queryset filtered by `query`.

#### `get_select_related_fields(model, config)`
Returns the list of queryset names that will be sent to an eventual call to the model's queryset `select_related()`.  The default list is generated by examining `config`'s `display_fields`.

### `SearchMixin`
**`appsearch.views.SearchMixin`**

Machinery for building a `Searcher` instance and inserting it into the template context.

#### `searcher_class`
**Default**: `Searcher`

#### `context_object_name`
**Default**: `"search"`

The name that the `Searcher` instance will be given in the template context.

#### `model_selection_form_class`
**Default**: `appsearch.forms.ModelSelectionForm`

The form that is responsible for the initial model dropdown in the search UI.  The default form provides an automatic verification against the registry, provides a ContentType id obfuscation, and defines a couple of methods to retrieve a validated instance's selected model class and associated `ModelSearch` configuration.

To provide a modified form, make sure it either subclasses `ModelSelectionForm` or provides the identical API methods `get_selected_model()` and `get_selected_model_configuration()`.

#### `constraint_form_class`
**Default**: `appsearch.forms.ConstraintForm`

An instance of this form class represents a row in the constraint builder UI, composed of fields that describe the constraint: the core AND/OR, the field to inspect, the operator, and the term or terms that describe the constraint.

By default, the `field` and `operator` fields have an empty choices list, since the choices depend on a valid selection in the model selection form.  The frontend Javascript queries the core appsearch AJAX views to look up the appropriate choices from the registry.  Consequently, the form's field-cleaning methods verify a valid selection.

All of the constraint form's fields are cleaned and database-ready values are returned.  For example, the field `type`, which describes if the constraint is an AND or OR operation is cleaned to `operator.and_` or `operator.or_`, respectively.  Accordingly, the `operator` field is cleaned to the actual queryset language path(s), such as `"related__lookup__path"`.

#### `constraint_formset_class`
**Default**: `appsearch.forms.ConstraintFormset`

The formset class used as the basis of `formset_factory()` creation.  The default form overrides an internal method to ensure that the model selection form's corresponding configuration is sent to the constructor of the constraint forms within.  It contains no other logic or overrides.

#### `get_model_selection_form_class()`
Returns `self.model_selection_form_class`

#### `get_constraint_form_class()`
Returns `self.constraint_form_class`

#### `get_constraint_formset_class()`
Returns `self.constraint_formset_class`

#### `form_template_name`
**Default**: `"appsearch/default_form.html"`

This default template includes the contents of the default templates at `search_form_template_name` and `results_list_template_name`.

#### `search_form_template_name`
**Default**: `"appsearch/search_form.html"`

Renders the search forms, not including the search results.

#### `results_list_template_name`
**Default**: `"appsearch/results_list.html"`

Renders the results list, not including the search forms.  The output of the template is blank if no search was executed on the current request.

#### `get_form_template_name()`
Returns `self.form_template_name`

#### `get_search_form_template_name()`
Returns `self.search_form_template_name`

#### `get_results_list_template_name()`
Returns `self.results_list_template_name`

#### `get_searcher_class()`
Returns `self.searcher_class`

#### `get_searcher_kwargs()`
Returns a dictionary of keyword arguments to be passed to the searcher constructor.  The default kwargs are the template names specified by the view.

#### `get_searcher()`
Returns an instantiated searcher, using the class provided by `get_searcher_class()` and the keyword arguments given by `get_searcher_kwargs()`.

#### `get_context_object_name()`
Returns `self.context_object_name`.

#### `get_context_data(**kwargs)`
Adds the `Searcher` instance to the context via the name given by `get_context_object_name()`

If the searcher instance reports that it is fully valid, the search will be executed during this method.

### `BaseSearchView`
**`appsearch.views.BaseSearchView`**

Inherits from `SearchMixin` and the built-in `TemplateView`.

### Build Process:
1.  Update the `__version_info__` inside of the application. Commit and push.
2.  Tag the release with the version. `git tag <version> -m "Release"; git push --tags`
3.  Build the release `rm -rf dist build *egg-info; python setup.py sdist bdist_wheel`
4.  Upload the data `twine upload dist/*`
