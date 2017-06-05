"""
MICROSITES API URLs
"""
from django.conf import settings
from django.conf.urls import patterns, url
from .views import MicrositesViewSet, MicrositesDetailView


urlpatterns = patterns(
    'microsite_configuration.views',
    url(r'^v1/microsites/$', MicrositesViewSet.as_view({'get': 'get', 'post': 'post'}), name="microsites-list"),
    url(r'^v1/microsites/(?P<pk>[0-9]+)/$', MicrositesDetailView.as_view({'get': 'get', 'put': 'put'}), name="microsite-detail")
)
