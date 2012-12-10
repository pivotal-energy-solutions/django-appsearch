from django.conf.urls.defaults import patterns, url

import appsearch
from appsearch.views import ModelListing, AjaxFillFields, AjaxConstraint

appsearch.autodiscover()

urlpatterns = patterns('',
    url(r'^$', ModelListing.as_view(), name='listing'),
    url(r'filters/$', AjaxFillFields.as_view(), name='filter'),
    url(r'constraint/$', AjaxConstraint.as_view(), name='constraint'),
)
