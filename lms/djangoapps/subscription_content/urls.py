from django.conf import settings
from django.conf.urls import patterns, url

urlpatterns = patterns(
    'subscription_content.views',
    url(r'^dashboard$', 'dashboard', name='subscription_dashboard'),
)
