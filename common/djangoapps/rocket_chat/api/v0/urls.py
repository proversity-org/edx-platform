"""
API v0 URLs.
"""
from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^credentials', views.RocketChatCredentials.as_view(), name='rocket_chat_credentials'),
]
