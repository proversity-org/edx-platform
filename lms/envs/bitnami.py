
""" Overrides for Bitnami-based installations. """

import os

from .aws import *

# Log configuration overrides
local_loglevel = ENV_TOKENS.get('LOCAL_LOGLEVEL', 'INFO')
LOGGING['handlers']['local'] = {
    'level': local_loglevel,
    'class': 'logging.handlers.RotatingFileHandler',
    'formatter': 'standard',
    'filename': os.path.join(LOG_DIR, 'edx.log'),
    'maxBytes': 1024 * 1024 * 2,
    'backupCount': 5,
}
LOGGING['handlers']['tracking'] = {
    'level': 'DEBUG',
    'class': 'logging.handlers.RotatingFileHandler',
    'formatter': 'standard',
    'filename': os.path.join(LOG_DIR, 'tracking.log'),
    'maxBytes': 1024 * 1024 * 2,
    'backupCount': 5,
}
LOGGING['loggers']['']['level'] = local_loglevel

update_module_store_settings(
    MODULESTORE,
    module_store_options={
        'fs_root': DATA_DIR,
    },
    xml_store_options={
        'data_dir': DATA_DIR,
    },
)

INSTALLED_APPS += ['import_export', 'systematic']
