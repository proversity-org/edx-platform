"""
 Custom backend for the memcache object to provide switching between two caches internally to be able to not lose asset during updates
"""

from django.core.cache.backends.memcached import MemcachedCache
import memcache
import inspect

from django.core.cache.backends.base import DEFAULT_TIMEOUT

import logging
log = logging.getLogger("CUSTOM CACHE")

class CustomMemcache(MemcachedCache):

    def __init__(self, server, params):
        print("custom memcache AAWWEE")
        super(CustomMemcache, self).__init__(server, params)

        cache_version_holder = memcache.Client(['localhost:11211'], debug=0)
        cache_version_holder.add('build_version', 0)
        cache_version_holder.add('run_version', 0)
        
        if self._is_build_calling(inspect.stack()):
            cache_version_holder.set('build_version', cache_version_holder.get('build_version')+1)
            self.version = cache_version_holder.get('build_version')
            log.error("BUILD IS CALLING USING THIS VERSION MAN {}".format(self.version))
            cache_version_holder.set('run_version', cache_version_holder.get('build_version'))
            log.error("INCREMENTING THE RUN VERSION MAN {}".format(cache_version_holder.get('run_version')))
        else:
            self.version = cache_version_holder.get('run_version')
            log.error("USING THIS VERSION MAN {}".format(self.version))


    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return super(CustomMemcache, self).add(key, value, timeout, self.version)


    def get(self, key, default=None, version=None):
        return super(CustomMemcache, self).get(key, default, self.version)


    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        return super(CustomMemcache, self).set(key, value, timeout, self.version)

    def delete(self, key, version=None):
        return super(CustomMemcache, self).delete(key, self.version)

    def get_many(self, keys, version=None):
        return super(CustomMemcache, self).get_many(keys, self.version)

    def incr(self, key, delta=1, version=None):
        return super(CustomMemcache, self).incr(key, delta, self.version)

    def decr(self, key, delta=1, version=None):
        return super(CustomMemcache, self).decr(key, delta, self.version)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        return super(CustomMemcache, self).set_many(data, timeout, self.version)

    def delete_many(self, keys, version=None):
        return super(CustomMemcache, self).delete_many(keys, self.version)

    def _is_build_calling(self, stack):
        column_len = len(stack[0])
        row_len = len(stack)
        for i in range(0, row_len):
            for j in range(column_len):
                if j == 0:
                    j = 1 
                if 'collectstatic' in str(stack[i][j]):
                    return True
        return False

    