from django.conf.urls.defaults import patterns, url, include

import appsearch
from appsearch.views import ConstraintsAjaxView

appsearch.autodiscover()

urlpatterns = patterns('',
    (r'^', include(patterns('',
        url(r'constraint/$', ConstraintsAjaxView.as_view(), name='constraints'),
    ), namespace='appsearch')),
)
