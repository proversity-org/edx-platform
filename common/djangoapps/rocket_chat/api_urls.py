
from django.conf.urls import include, url

urlpatterns = [
    url(r'^', include('rocket_chat.api.urls', namespace='api')),
]
