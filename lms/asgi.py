"""
ASGI config for LMS.

This module contains the ASGI application used by Django's development server
and any production ASGI deployments.
This is necessary for the openedx-proversity-notifications plugin.
https://github.com/proversity-org/openedx-proversity-notifications
"""
import os
from channels.asgi import get_channel_layer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lms.envs.aws")
channel_layer = get_channel_layer()
