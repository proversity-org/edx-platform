from rest_framework import permissions


class IsSuperuser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or obj.user == request.user

    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser \
               or (user.username == request.GET.get('username')) \
               or (user.username == getattr(request, 'data', {}).get('username')) \
               or (user.username == getattr(view, 'kwargs', {}).get('username'))
