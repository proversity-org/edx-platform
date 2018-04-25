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
log = logging.getLogger("CUSTOM CACHE")

class CustomCachedFilesMixin(HashedFilesMixin):

    def __init__(self, *args, **kwargs):
        super(CustomCachedFilesMixin, self).__init__(*args, **kwargs)


        cache_version_holder = memcache.Client(['localhost:11211'], debug=0)
        if not cache_version_holder.get('build_version'):
            cache_version_holder.add('build_version', 'staticfiles_2') 
        if not cache_version_holder.get('run_version'):
            cache_version_holder.add('run_version', 'staticfiles')
        if not cache_version_holder.get('has_lms_ran'):
            cache_version_holder.add('has_lms_ran', 'no')
        if not cache_version_holder.get('has_cms_ran'):
            cache_version_holder.add('has_cms_ran', 'no')


        print("CUSTOM STORAGE GUY")
        try:

            if self._is_build_calling(inspect.stack(), cache_version_holder):
                self.hashed_files = _MappingCache(caches[cache_version_holder.get('build_version')])
                log.error("Build is calling setting hashed files to {}".format(cache_version_holder.get('build_version')))
                if self._has_both_ran(cache_version_holder):
                    cache_version_holder.set('run_version', cache_version_holder.get('build_version'))
                    log.error("Setting the run_version = build_version")
                    if cache_version_holder.get('build_version') == 'staticfiles_2':
                        log.error("updating build_version to staticfiles")
                        cache_version_holder.set('build_version', 'staticfiles')
                    else:
                        log.error("updating build_version to staticfiles_2")
                        cache_version_holder.set('build_version', 'staticfiles_2')
            else:
                log.error("run called, starting hashed files version {}".format(cache_version_holder.get('run_version')))
                self.hashed_files = _MappingCache(caches[cache_version_holder.get('run_version')])
        except InvalidCacheBackendError:
            # Use the default backend
            self.hashed_files = _MappingCache(default_cache)

    def hash_key(self, name):
        key = hashlib.md5(force_bytes(self.clean_name(name))).hexdigest()
        return 'staticfiles:%s' % key

    def _is_build_calling(self, stack,cache_version_holder):
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
        if settings.ROOT_URLCONF == 'lms.urls':
            cache_version_holder.set('has_lms_ran', 'yes')
            print("AAAAA LMS CALLING")
        if settings.ROOT_URLCONF == 'cms.urls':
            print("AAAAA CMS CALLING")
            cache_version_holder.set('has_cms_ran', 'yes')
        if cache_version_holder.get('has_lms_ran') == 'yes' and cache_version_holder.get('has_lms_ran') == 'yes':
            print("BOTH HAS RAN")
            cache_version_holder.set('has_lms_ran', 'no')
            cache_version_holder.set('has_cms_ran', 'no')
            return True
        return False
            

