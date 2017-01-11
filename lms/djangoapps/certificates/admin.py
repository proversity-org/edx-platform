"""
django admin pages for certificates models
"""
<<<<<<< HEAD
=======
from django.contrib import admin
from django import forms
from django.contrib import messages
>>>>>>> Make Certificate html view configuration editable
from config_models.admin import ConfigurationModelAdmin
from django import forms
from django.contrib import admin

from certificates.models import (
    CertificateGenerationConfiguration,
    CertificateGenerationCourseSetting,
    CertificateHtmlViewConfiguration,
    CertificateTemplate,
    CertificateTemplateAsset,
    GeneratedCertificate
)
from util.organizations_helpers import get_organizations


class CertificateTemplateForm(forms.ModelForm):
    """
    Django admin form for CertificateTemplate model
    """
    def __init__(self, *args, **kwargs):
        super(CertificateTemplateForm, self).__init__(*args, **kwargs)
        organizations = get_organizations()
        org_choices = [(org["id"], org["name"]) for org in organizations]
        org_choices.insert(0, ('', 'None'))
        self.fields['organization_id'] = forms.TypedChoiceField(
            choices=org_choices, required=False, coerce=int, empty_value=None
        )

    class Meta(object):
        model = CertificateTemplate
        fields = '__all__'


class CertificateTemplateAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateTemplate model
    """
    list_display = ('name', 'description', 'organization_id', 'course_key', 'mode', 'is_active')
    form = CertificateTemplateForm


class CertificateHtmlViewConfigurationFrom(forms.ModelForm):

    class Meta:
        model = CertificateHtmlViewConfiguration
        fields = ['configuration']


class CertificateHtmlViewConfigurationAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateHtmlViewConfiguration model
    """
    list_display = ('id', 'change_date', 'changed_by', 'configuration', 'enabled',)
    form = CertificateHtmlViewConfigurationFrom
    actions = ['enable_configuration', 'delete_configuration']

    def enable_configuration(self, request, queryset):
        if queryset.count() == 1:
            CertificateHtmlViewConfiguration.objects.all().update(enabled=False)
            queryset.update(enabled=True)
            messages.success(request, "This configuration was successfully chosen.")
        else:
            messages.error(request, "You can only enable only one configuration.")

    enable_configuration.short_description = "Enable configuration"

    def delete_configuration(self, request, queryset):

        for config_query in queryset:
            if config_query.enabled == False:
                config_query.delete()
                messages.success(request, "The configuration was successfully deleted.")
            else:
                messages.error(request, "You can not delete an active configuration.")

    delete_configuration.short_description = "Delete selected configuration."

    def has_delete_permission(self, request, obj=None):
        return False


    def get_actions(self, request):
        actions = super(CertificateHtmlViewConfigurationAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class CertificateTemplateAssetAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateTemplateAsset model
    """
    list_display = ('description', 'asset_slug',)
    prepopulated_fields = {"asset_slug": ("description",)}


class GeneratedCertificateAdmin(admin.ModelAdmin):
    """
    Django admin customizations for GeneratedCertificate model
    """
    raw_id_fields = ('user',)
    show_full_result_count = False
    search_fields = ('course_id', 'user__username')
    list_display = ('id', 'course_id', 'mode', 'user')


class CertificateGenerationCourseSettingAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateGenerationCourseSetting model
    """
    list_display = ('course_key', 'enabled')
    search_fields = ('course_key',)
    show_full_result_count = False


admin.site.register(CertificateGenerationConfiguration)
admin.site.register(CertificateGenerationCourseSetting, CertificateGenerationCourseSettingAdmin)
admin.site.register(CertificateHtmlViewConfiguration, CertificateHtmlViewConfigurationAdmin)
admin.site.register(CertificateTemplate, CertificateTemplateAdmin)
admin.site.register(CertificateTemplateAsset, CertificateTemplateAssetAdmin)
admin.site.register(GeneratedCertificate, GeneratedCertificateAdmin)