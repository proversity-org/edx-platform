
from django.conf.urls import include, url

from rocket_chat import views

urlpatterns = [

    url(r'^api/', include('rocket_chat.api.urls', namespace='api')),
    url(r'', views.rocket_chat_discussion, name='rocket_chat_discussion'),
]
