from rest_framework import serializers


class UserReportSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_login = serializers.DateTimeField()
    last_login = serializers.DateTimeField()
    days_since_last_login = serializers.IntegerField()
    completed_activities = serializers.IntegerField()
    total_program_activities = serializers.IntegerField()


class CompletionReportSerializer(serializers.Serializer):
    status = serializers.CharField()
    result = serializers.ListField(child=UserReportSerializer())
    link = serializers.URLField(max_length=200)
