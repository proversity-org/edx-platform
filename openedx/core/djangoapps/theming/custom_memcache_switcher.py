"""
 Custom backend for the memcache object to provide switching between two caches internally to be able to not lose asset during updates
"""

from django.core.cache.backends.memcached import BaseMemcachedCache
import memcache
import inspect
from django.contrib.staticfiles.storage import HashedFilesMixin, _MappingCache

from django.conf import settings

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache import (
    InvalidCacheBackendError, cache as default_cache, caches,
)

import logging
log = logging.getLogger(__name__)

class CustomCachedFilesMixin(HashedFilesMixin):

    def __init__(self, *args, **kwargs):
        super(CustomCachedFilesMixin, self).__init__(*args, **kwargs)

        # Setup the version holder cache.
        cache_version_holder = memcache.Client(['localhost:11211'], debug=0)
        if not cache_version_holder.get('build_version'):
            cache_version_holder.add('build_version', 'staticfiles_2') 
        if not cache_version_holder.get('run_version'):
            cache_version_holder.add('run_version', 'staticfiles_1')
        if not cache_version_holder.get('has_lms_ran'):
            cache_version_holder.add('has_lms_ran', 'no')
        if not cache_version_holder.get('has_cms_ran'):
            cache_version_holder.add('has_cms_ran', 'no')


        try:

            if self._is_build_calling(inspect.stack(), cache_version_holder):
                self.hashed_files = _MappingCache(caches[cache_version_holder.get('build_version')])
                if self._has_both_ran(cache_version_holder):
                    cache_version_holder.set('run_version', cache_version_holder.get('build_version'))
                    if cache_version_holder.get('build_version') == 'staticfiles_2':
                        cache_version_holder.set('build_version', 'staticfiles_1')
                    else:
                        cache_version_holder.set('build_version', 'staticfiles_2')
            else:
                self.hashed_files = _MappingCache(caches[cache_version_holder.get('run_version')])
        except InvalidCacheBackendError:
            # Use the default backend
            self.hashed_files = _MappingCache(default_cache)
            log.error("Invalid backends provided, check the CACHES setting in the *.env.json files. staticfiles_1 and staticfiles_2")

    def hash_key(self, name):
        key = hashlib.md5(force_bytes(self.clean_name(name))).hexdigest()
        return 'staticfiles:%s' % key

    def _is_build_calling(self, stack,cache_version_holder):
        """
        Utility function to inspect the stack and return if the collectstatic command was issued in the call stack
        """
        column_len = len(stack[0])
        row_len = len(stack)
        calling = False
        for i in range(0, row_len):
            for j in range(column_len):
                if j == 0:
                    j = 1
                if 'collectstatic' in str(stack[i][j]):
                    calling = True
        return calling

    def _has_both_ran(self, cache_version_holder):
        """
        Utility function to detect which of the two systems is being called and set that they have been build as assets.
        If both was built the values will be reset and we start a fresh.
        """
        if settings.ROOT_URLCONF == 'lms.urls':
            cache_version_holder.set('has_lms_ran', 'yes')
        if settings.ROOT_URLCONF == 'cms.urls':
            cache_version_holder.set('has_cms_ran', 'yes')
        if cache_version_holder.get('has_lms_ran') == 'yes' and cache_version_holder.get('has_lms_ran') == 'yes':
            cache_version_holder.set('has_lms_ran', 'no')
            cache_version_holder.set('has_cms_ran', 'no')
            return True
        return False
            

