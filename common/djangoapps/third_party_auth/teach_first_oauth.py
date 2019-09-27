"""
Custom oAuth backend for the Teach First instance.
"""
from django.conf import settings
from social_core.backends.oauth import BaseOAuth2


class TeachFirstOAuth2(BaseOAuth2):
    """
    TeachFirst OAuth2 authentication backend.
    """
    settings_dict = settings.CUSTOM_OAUTH_BACKEND_SETTINGS.get('teachfirst', {})
    AUTHORIZATION_URL = settings_dict.get('AUTH_URL', '')
    ACCESS_TOKEN_URL = settings_dict.get('ACCESS_TOKEN_URL', '')
    USER_DATA_URL = settings_dict.get('USER_DATA_URL', '')
    REDIRECT_STATE = False
    STATE_PARAMETER = False
    ACCESS_TOKEN_METHOD = 'POST'
    name = 'teachfirst-oauth2'

    def auth_complete(self, *args, **kwargs):
        """
        Completes the login process, must return a user instance.
        """
        self.process_error(self.data)

        state = self.validate_state()

        response = self.request_access_token(
            self.access_token_url(),
            data=self.auth_complete_params(state),
            headers=self.auth_headers(),
            auth=self.auth_complete_credentials(),
            method=self.ACCESS_TOKEN_METHOD,
        )

        self.process_error(response)

        return self.do_auth(
            response.get('access_token', ''),
            response=response,
            *args,
            **kwargs
        )

    def auth_complete_params(self, state=None):
        """
        Returns the TeachFirst oAuth params.
        """
        client_id, client_secret = self.get_key_and_secret()

        return {
            'state': state,
            'grant_type': 'authorization_code',
            'code': self.data.get('code', ''),  # server response code
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': self.get_redirect_uri(state),
        }

    def get_user_details(self, response):
        """
        Returns the user details.
        """
        return {
            'username': response.get('username', ''),
            'email': response.get('mail', ''),
            'fullname': response.get('fullname', ''),
            'salesforceid': response.get('salesforceid', ''),
        }

    def user_data(self, access_token, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns the user data.
        """
        response = self.get_json(
            self.USER_DATA_URL,
            headers={
                'Authorization': 'Bearer {}'.format(access_token),
            },
        )

        return response[0] if response else {}

    def get_user_id(self, details, response):  # pylint: disable=unused-argument
        """
        Returns the user id.
        """
        return details.get('salesforceid', '')

    def extra_data(self, user, uid, response, details=None, *args, **kwargs):
        """
        Returns the extra_data.
        """
        data = super(TeachFirstOAuth2, self).extra_data(
            user,
            uid,
            response,
            details,
            *args,
            **kwargs
        )

        data['access_token'] = response.get('access_token', '') or kwargs.get('access_token', '')
        # Add Salesforce ID to user social auth extra data
        data['salesforceid'] = response.get('salesforceid')

        return data
