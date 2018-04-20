"""
 Custom backend for the memcache object to provide switching between two caches internally to be able to not lose asset during updates
"""

from django.core.cache.backends.memcached import MemcachedCache
import memcache
from django.core.cache import cache

from django.core.cache.backends.base import DEFAULT_TIMEOUT

class CustomMemcache(MemcachedCache):

    def __init__(self, server, params):
        print("custom memcache AAWWEE")
        super(CustomMemcache, self).__init__(server, params)

        cache_version_holder = memcache.Client(['localhost:11211'], debug=0)

        if not cache_version_holder.get('build_version') and not cache_version_holder.get('run_version'):
            cache_version_holder.add('build_version', 1)
            cache_version_holder.add('run_version', 0)
            self.version = cache_version_holder.get('build_version')
            print("USING THIS VERSION MAN {}".format(self.version))
        elif cache_version_holder.get('build_version') > cache_version_holder.get('run_version'):
            cache_version_holder.set('run_version',cache_version_holder.get('build_version'))
            self.version = cache_version_holder.get('run_version')
            print("USING THIS VERSION MAN {}".format(self.version))
        elif cache_version_holder.get('build_version') == cache_version_holder.get('run_version'):
            cache_version_holder.set('build_version', cache_version_holder.get('build_version') + 1)
            self.version = cache_version_holder.get('build_version')
            print("USING THIS VERSION MAN {}".format(self.version))




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

    