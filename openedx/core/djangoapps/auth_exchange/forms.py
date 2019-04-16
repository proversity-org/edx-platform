"""
Forms to support third-party to first-party OAuth 2.0 access token exchange
"""
import provider.constants
import requests
from django.contrib.auth.models import User
from django.forms import CharField, BooleanField
from edx_oauth2_provider.constants import SCOPE_NAMES
from oauth2_provider.models import Application
from provider.forms import OAuthForm, OAuthValidationError
from provider.oauth2.forms import ScopeChoiceField, ScopeMixin
from provider.oauth2.models import Client
from requests import HTTPError
from social_core.backends import oauth as social_oauth
from social_core.exceptions import AuthException

from third_party_auth import pipeline

import logging
log = logging.getLogger("edx.student")


class AccessTokenExchangeForm(ScopeMixin, OAuthForm):
    """Form for access token exchange endpoint"""
    access_token = CharField(required=False)
    scope = ScopeChoiceField(choices=SCOPE_NAMES, required=False)
    client_id = CharField(required=False)
    email = CharField(required=False)
    is_linkedin_mobile = BooleanField(required=False)

    def __init__(self, request, oauth2_adapter, *args, **kwargs):
        super(AccessTokenExchangeForm, self).__init__(*args, **kwargs)
        self.request = request
        self.oauth2_adapter = oauth2_adapter

    def _require_oauth_field(self, field_name):
        """
        Raise an appropriate OAuthValidationError error if the field is missing
        """
        field_val = self.cleaned_data.get(field_name)
        if not field_val:
            raise OAuthValidationError(
                {
                    "error": "invalid_request",
                    "error_description": "{} is required".format(field_name),
                }
            )
        return field_val

    def authenticate_to_linkedin_using_msdk(self, access_token, email):
        log.error("authenticate_to_linkedin_using_msdk")
        fields = ':(email-address,first-name,headline,id,industry,last-name,location,specialties,summary)'
        params = {'format': 'json'}
        headers = {'x-li-src': 'msdk', 'Authorization': 'Bearer ' + access_token}
        url = 'https://api.linkedin.com/v1/people/~%s' % fields
        r = requests.get(url, params=params, headers=headers)
        if r.status_code == 200:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist:
                return None
        else:
            return None

    def clean_access_token(self):
        """
        Validates and returns the "access_token" field.
        """
        return self._require_oauth_field("access_token")

    def clean_client_id(self):
        """
        Validates and returns the "client_id" field.
        """
        return self._require_oauth_field("client_id")

    def clean(self):
        if self._errors:
            return {}
        log.error("===== clean =====")
        backend = self.request.backend
        if not isinstance(backend, social_oauth.BaseOAuth2):
            raise OAuthValidationError(
                {
                    "error": "invalid_request",
                    "error_description": "{} is not a supported provider".format(backend.name),
                }
            )

        self.request.session[pipeline.AUTH_ENTRY_KEY] = pipeline.AUTH_ENTRY_LOGIN_API

        client_id = self.cleaned_data["client_id"]
        try:
            client = self.oauth2_adapter.get_client(client_id=client_id)
        except (Client.DoesNotExist, Application.DoesNotExist):
            raise OAuthValidationError(
                {
                    "error": "invalid_client",
                    "error_description": "{} is not a valid client_id".format(client_id),
                }
            )
        if client.client_type not in [provider.constants.PUBLIC, Application.CLIENT_PUBLIC]:
            raise OAuthValidationError(
                {
                    # invalid_client isn't really the right code, but this mirrors
                    # https://github.com/edx/django-oauth2-provider/blob/edx/provider/oauth2/forms.py#L331
                    "error": "invalid_client",
                    "error_description": "{} is not a public client".format(client_id),
                }
            )
        self.cleaned_data["client"] = client

        user = None
        access_token = self.cleaned_data.get("access_token")
        try:
            user = backend.do_auth(access_token, allow_inactive_user=True)

            if (self.cleaned_data.get('is_linkedin_mobile', False)):
                user =\
                    self.authenticate_to_linkedin_using_msdk(
                        self.cleaned_data.get("access_token"),
                        self.cleaned_data.get("email")
                    )
                log.error(user)
            else:
                user = backend.do_auth(self.cleaned_data.get("access_token"), allow_inactive_user=True)

        except (HTTPError, AuthException):
            pass
        if user and isinstance(user, User):
            self.cleaned_data["user"] = user
        else:
            # Ensure user does not re-enter the pipeline
            self.request.social_strategy.clean_partial_pipeline(access_token)
            raise OAuthValidationError(
                {
                    "error": "invalid_grant",
                    "error_description": "access_token is not valid",
                }
            )

        return self.cleaned_data
