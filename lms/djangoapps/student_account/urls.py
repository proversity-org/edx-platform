from django.conf import settings
<<<<<<< HEAD
<<<<<<< HEAD
from django.conf.urls import patterns, url
=======
from .views import RecoverPasswordView
>>>>>>> add recover password endpoint
=======
from .views import RecoverPasswordView
>>>>>>> Proversity/staging (#411)

urlpatterns = []

if settings.FEATURES.get('ENABLE_COMBINED_LOGIN_REGISTRATION'):
    urlpatterns += patterns(
        'student_account.views',
        url(r'^password$', 'password_change_request_handler', name='password_change_request'),
        url(r'^recover-password$', RecoverPasswordView.as_view({'post': 'post'}), name="restrecover-password"),
    )

urlpatterns += patterns(
    'student_account.views',
    url(r'^finish_auth$', 'finish_auth', name='finish_auth'),
    url(r'^settings$', 'account_settings', name='account_settings'),
)
