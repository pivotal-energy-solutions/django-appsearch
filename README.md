# django-appsearch

Framework and generic app for cross-model searches on a single page

## Usage

Appsearch integration is composed of a few separate parts.  In the simplest default setup, you must at least do the following:

* Register models with appsearch
* Include appsearch.urls (which has its own "appsearch" namespace already built in)
* Create your main view where the search page should appear
* Create a simple template where the search form can be rendered

There are ways to customize the templates, modify the search queryset, etc, which is covered after the basic introduction.

### Model registration


Patterned after `django.contrib.admin` interface, appsearch includes a `registry` submodule, which contains a `ModelSearch` class (along the lines of the admin's `ModelAdmin`), and a default registry object called `search`.

`ModelSearch` has a few basic options, the most important of which are `search_fields` and `display_fields`.

We'll use this example base model for registration, which reaches out to a couple of other fake models for the sake of demonstration:

    # car/models.py
    
    class Car(models.Model):
        year = models.PositiveIntegerField()
        make = models.ForeignKey(CarMake)
        model = models.ForeignKey(CarModel)
        
        owners = models.ManyToManyField(User)
        
        nickname = models.CharField(max_length=50)
        adoption_story = models.TextField()

##### `search_fields`
    
To register this model, place a `search.py` submodule in your app's directory and include at least this basic registration code.  We'll leave out the majority of `Car`'s fields for clarity:

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

`search_fields` is an iterable whose items describe searchable fields.  The order that the fields are listed here will be respected in the appsearch UI.  An item in the list can be a string if it directly describes a model field name.  The field will be looked up and its `verbose_name` stored for use in the UI.  To explicitly declare a "verbose name" for use within the appsearch UI, you can make the string a 2-tuple of the verbose name and the field name:

    search_fields = (
        'year',
        ("Name", 'nickname'),
        'adoption_story',
    )

To pull related fields into the mix, an item can instead be a single-entry dictionary, mapping the attribute to a nested structure following the same format:

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
    
This syntax reduces potentially repetitive query language such as `"owners__username"`, `"owners__first_name"`, and `"owners__last_name"`.

Any related field that doesn't supply its own verbose name here in the search configuration will be displayed with the related model's `verbose_name` in front of it.  In other words, to prevent the search UI from presenting an owner's `"first_name"` field as if it were the car's first name, the UI will prefix the field's name with the `User` model's verbose_name.  In this example, `first_name` would be shown as "User first name".

To prevent the automatic prefix, you can supply your own verbose name as previously shown:

    search_fields = (
        # ...
        {'owners': (
            ("Username", 'username'), # would have been "User username"
            ("User's First name", "first_name"), # would have been "User first name"
            ("User's Last name", "last_name"), # would have been "User last name"
        )},
    )

Related fields can be recursively referenced:

    search_fields = (
        # ...
        {'owners': (
            'username', # displayed as "User username"
            {'groups': (
                'name', # displayed as "Group name"
            )},
        )},
    )

##### `display_fields`

By default, the results table shown by appsearch will include all local fields on the model.  To explicitly declare the field list, your configuration can include another attribute `display_fields`, which follows a similar format to `search_fields`:

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

`display_fields` is an iterable of items, either strings or 2-tuples of (verbosename, fieldname).  As with `search_fields`, fields will have their `verbose_name` automatically retrieved, unless it is supplied explicitly in the configuration.

A field isn't necessarily required to be a database field; in the example above, we've placed an "Owners" column in the table headers, and the field is actually a method name.  This is convenient, but be careful not generate too many queries outside of appsearch's control!

The first item in this list will be converted into a link, wrapping the value with a simple snippet of HTML: `<a href="{{ object.get_absolute_url }}">{{ value }}</a>`

appsearch will examine `display_fields` to discover how to best issue a `select_related()` call to the search results queryset, which helps keep the automatic query count low.

### `appsearch.urls`

The dynamic search form generated by appsearch will fetch the field and valid operator lists from the server via a couple of simple Ajax-only views.  These views simply inspect the registry and
return valid choices as they are configured in the various ModelSearch instances throughout the project.

    # project/urls.py
    
    urlpatterns = patterns('',
        (r'^', include('appsearch.urls')),
        # ...
    )

The default views are available at the named urls "appsearch:constraint-fields" and "appsearch:constraint-operators".  Typically, you won't need to know that, but these are the names that the default template will use to initialize the client-side javascript.

If you want to include the urls within another namespace, such as `"mysearchapp:"`, you are free to do so, but will need to make sure you configure [the main view](#the-main-view) to know about that namespace.

### The main view

The urls included in appsearch only handle the ajax requests that occur during user interaction on the main template.  That means you need to declare your own starting point for the client to initially visit and configure a search.

`BaseSearchView` is a simple `TemplateView` subclass that also inherits from `appsearch.views.SearchMixin`.  For a completely vanilla behavior, you could include the `BaseSearchView` directly:

    # project/mysearchapp/urls.py
    
    from django.conf.urls.defaults import patterns, url
    from appsearch.views import BaseSearchView
    
    urlpatterns = patterns('',
        url(r'^search/$', BaseSearchView.as_view(template_name="search.html")),
    )

Remember, because `BaseSearchView` is pretty much just a `TemplateView`, you need to give it a `template_name` value.  Don't worry though, since the view is inheriting machinery for making the search form trivial to render.
    
Alternately, you can subclass `BaseSearchView` and gain access to extra flexibility:

    # project/mysearchapp/views.py
    
    from appsearch.views import BaseSearchView
    
    class SearchView(BaseSearchView):
        template_name = "search.html"
    
#### URL namespace prefix

If you've mounted appsearch.urls in a namespace of your own, such as "search:", the view needs to know about it so that it can help to simplify the footwork of rendering the appsearch templates.

The `BaseSearchView` constructs a utility object, `appsearch.utils.Searcher` which will actually do the heavy lifting.  It is constructed with the help of a set of keyword arguments returned from `BaseSearchView.get_searcher_kwargs()`.  Override this method and add `"url_namespace"` to the dictionary:

    class SearchView(BaseSearchView):
        template_name = "search.html"
        
        def get_searcher_kwargs(self):
            kwargs = super(SearchView, self).get_searcher_kwargs()
            kwargs['url_namespace'] = "search"

#### search.html

You're free to make whatever template you want for the search to exist on.  By default, all you need to do is render the ``search`` context variable into your template:

    {# search.html #}
    
    {% block content %}
        {{ search }}
    {% endblock %}

There are plenty of ways to customize how the form is rendered and how the Javascript behaves, but this is enough to get a fully functioning search implementation.

### That's it!

With the ajax urls mounted, your instance of `BaseSearchView` in play, and your model configurations registered, and your template dumping out the generated form, you're finished.
