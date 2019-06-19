"""
A custom Strategy for python-social-auth that allows us to fetch configuration from
ConfigurationModels rather than django.settings
"""

from social_core.backends.oauth import OAuthAuth
from social_django.strategy import DjangoStrategy

from .models import OAuth2ProviderConfig
from .pipeline import get as get_pipeline_from_request
from .pipeline import AUTH_ENTRY_CUSTOM
from .provider import Registry


class ConfigurationModelStrategy(DjangoStrategy):
    """
    A DjangoStrategy customized to load settings from ConfigurationModels
    for upstream python-social-auth backends that we cannot otherwise modify.
    """
    def setting(self, name, default=None, backend=None):
        """
        Load the setting from a ConfigurationModel if possible, or fall back to the normal
        Django settings lookup.

        OAuthAuth subclasses will call this method for every setting they want to look up.
        SAMLAuthBackend subclasses will call this method only after first checking if the
            setting 'name' is configured via SAMLProviderConfig.
        LTIAuthBackend subclasses will call this method only after first checking if the
            setting 'name' is configured via LTIProviderConfig.
        """
        if isinstance(backend, OAuthAuth):
            raise_exception = False
            oauth2_slugs = OAuth2ProviderConfig.key_values('provider_slug', flat=True)
            for oauth2_slug in oauth2_slugs:
                provider = OAuth2ProviderConfig.current(oauth2_slug)
                if provider.backend_name == backend.name:
                    if provider.enabled_for_current_site:
                        raise_exception = False
                        try:
                            return provider.get_setting(name)
                        except KeyError:
                            break
                    else:
                        raise_exception = True
            if raise_exception:
                raise Exception("Can't fetch setting of a disabled backend/provider.")

        # special case handling of login error URL if we're using a custom auth entry point:
        if name == 'LOGIN_ERROR_URL':
            auth_entry = self.request.session.get('auth_entry')
            if auth_entry and auth_entry in AUTH_ENTRY_CUSTOM:
                error_url = AUTH_ENTRY_CUSTOM[auth_entry].get('error_url')
                if error_url:
                    return error_url

        # Special case: we want to get this particular setting directly from the provider database
        # entry if possible; if we don't have the information, fall back to the default behavior.
        if name == 'MAX_SESSION_LENGTH':
            running_pipeline = get_pipeline_from_request(self.request) if self.request else None
            if running_pipeline is not None:
                provider_config = Registry.get_from_pipeline(running_pipeline)
                if provider_config:
                    return provider_config.max_session_length

        # At this point, we know 'name' is not set in a [OAuth2|LTI|SAML]ProviderConfig row.
        # It's probably a global Django setting like 'FIELDS_STORED_IN_SESSION':
        return super(ConfigurationModelStrategy, self).setting(name, default, backend)
