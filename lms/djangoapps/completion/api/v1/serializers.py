from rest_framework import serializers


class UserReportSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_login = serializers.DateTimeField(format="%Y/%m/%d %H:%M:%S")
    last_login = serializers.DateTimeField(format="%Y/%m/%d %H:%M:%S")
    completed_activities = serializers.IntegerField()
    total_program_activities = serializers.IntegerField()


class CompletionReportSerializer(serializers.Serializer):
    status = serializers.CharField()
    result = UserReportSerializer(many=True)
    link = serializers.URLField(max_length=200)
