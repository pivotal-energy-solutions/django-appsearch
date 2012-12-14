from django.conf.urls.defaults import patterns, url, include

import appsearch
from appsearch.views import ConstraintFieldsAjaxView, ConstraintOperatorsAjaxView

appsearch.autodiscover()

urlpatterns = patterns('',
    (r'^', include(patterns('',
        url(r'constraint/$', ConstraintFieldsAjaxView.as_view(), name='constraint-fields'),
        url(r'operators/$', ConstraintOperatorsAjaxView.as_view(), name='constraint-operators'),
    ), namespace='appsearch')),
)
