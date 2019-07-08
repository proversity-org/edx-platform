"""
Admin site bindings for student account models.
"""

from django.contrib import admin

from lms.djangoapps.student_account.models import UserSalesforceContactId

class UserSalesforceContactIdAdmin(admin.ModelAdmin):
    """
    Admin class for UserSalesforceContactId model.
    """
    fields = ('user', 'contact_id', 'contact_id_source',)
    list_display = ('user', 'contact_id', 'contact_id_source',)
    list_filter = ('contact_id_source',)
    search_fields = ('user__email',)


admin.site.register(UserSalesforceContactId, UserSalesforceContactIdAdmin)
