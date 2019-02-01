from django.conf import settings
from social_core.backends.oauth import BaseOAuth2
import logging

log = logging.getLogger(__name__)


class TeachFirstOAuth2(BaseOAuth2):
    """TeachFirst OAuth2 authentication backend."""
    settings_dict = settings.CUSTOM_BACKENDS.get('teachfirst')
    name = 'teachfirst-oauth2'
    REDIRECT_STATE = False
    STATE_PARAMETER = False
    AUTHORIZATION_URL = settings_dict.get('AUTH_URL')
    ACCESS_TOKEN_URL = settings_dict.get('ACCESS_TOKEN_URL')
    USER_DATA_URL = settings_dict.get('USER_DATA_URL')
    ACCESS_TOKEN_METHOD = 'POST'

    def auth_complete(self, *args, **kwargs):
        """Completes login process, must return user instance"""
        self.process_error(self.data)
        state = self.validate_state()

        response = self.request_access_token(
            self.access_token_url(),
            data=self.auth_complete_params(state),
            headers=self.auth_headers(),
            auth=self.auth_complete_credentials(),
            method=self.ACCESS_TOKEN_METHOD
        )
        self.process_error(response)
        return self.do_auth(response['access_token'], response=response,
                            *args, **kwargs)

    def auth_complete_params(self, state=None):
        client_id, client_secret = self.get_key_and_secret()
        return {
            'state': state,
            'grant_type': 'authorization_code',
            'code': self.data.get('code', ''),  # server response code
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': self.get_redirect_uri(state)
        }

    def get_user_details(self, response):
        return {'username': response.get('username'),
                'email': response.get('mail'),
                'fullname': response.get('fullname')}

    def user_data(self, access_token, *args, **kwargs):
        response = self.get_json(self.USER_DATA_URL, headers={
            'Authorization': 'Bearer {}'.format(access_token)
        })
        return response[0]

    def get_user_id(self, details, response):
        return details.get('email')
