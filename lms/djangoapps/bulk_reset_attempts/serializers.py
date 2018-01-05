"""
Serializers for Bulk Enrollment.
"""
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework import serializers


class StringListField(serializers.ListField):
    def to_internal_value(self, data):
        if not data:
            return []
        if isinstance(data, list):
            data = data[0]
        return data.split(',')


class BulkResetStudentAttemptsSerializer(serializers.Serializer):
    course_id = serializers.CharField(required=True)
    identifiers = StringListField(required=True)
    problems = StringListField(required=True)
    reset_state = serializers.BooleanField(default=False)
    email_extension = serializers.CharField(required=False)
