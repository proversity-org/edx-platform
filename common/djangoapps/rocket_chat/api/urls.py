"""
Api URLs.
"""
from django.conf.urls import include, url

urlpatterns = [
    url(r'^v0/', include('rocket_chat.api.v0.urls', namespace='v0')),
]
