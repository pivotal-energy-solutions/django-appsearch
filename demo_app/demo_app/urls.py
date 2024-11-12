"""demo_app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from django.views.generic import TemplateView

import appsearch
from appsearch.views import BaseSearchView


appsearch.autodiscover()

urlpatterns = [
    path("", TemplateView.as_view(template_name="base.html"), name="home"),
    path("admin/", admin.site.urls),
    path("accounts/login/", LoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("search/", BaseSearchView.as_view(template_name="appsearch/search.html"), name="search"),
]

if settings.DEBUG:
    # Media
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
