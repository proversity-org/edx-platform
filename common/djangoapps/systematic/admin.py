from django.contrib import admin

from django.contrib.auth.models import User
from django.contrib.admin.sites import NotRegistered

from django.utils.decorators import method_decorator

from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from student.admin import UserAdmin, UserProfileInline

from .resources import UserResource
from import_export.admin import ImportExportModelAdmin

csrf_protect_m = method_decorator(csrf_protect)
sensitive_post_parameters_m = method_decorator(sensitive_post_parameters())

try:
    admin.site.unregister(User)
except NotRegistered:
    pass


class CustomUserAdmin(UserAdmin, ImportExportModelAdmin):
    resource_class = UserResource

admin.site.register(User, CustomUserAdmin)
