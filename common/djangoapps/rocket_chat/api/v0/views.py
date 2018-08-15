import logging

from django.core.cache import cache

from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework import status

from opaque_keys.edx.keys import CourseKey

from rocket_chat.utils import (
    get_rocket_chat_settings,
    initialize_api_rocket_chat,
    create_user,
    get_subscriptions_rids,
    logout,
    create_token,
)
from .serializers import RocketChatCredentialsSerializer, RocketChatChangeRoleSerializer

LOG = logging.getLogger(__name__)


class RocketChatCredentials(APIView):

    authentication_classes = (
        SessionAuthentication,
    )
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
        This returns a Json with the  user credentials in order to use the rocketchat api methods outside of the server
        """
        user = request.user
        course_id = request.GET.get("courseId")

        if not course_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        course_key = CourseKey.from_string(course_id)

        rocket_chat_settings = get_rocket_chat_settings()

        api_rocket_chat = initialize_api_rocket_chat(rocket_chat_settings)

        if api_rocket_chat:

            user_info = api_rocket_chat.users_info(username=user.username)

            try:
                user_info = user_info.json()
                if not user_info.get('success', False):
                    create_user(api_rocket_chat, user, course_key)
            except AttributeError:
                LOG.error("Rocketchat API can not get the user information")
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            response = create_token(api_rocket_chat, user)

            if not response:
                LOG.error("Rocketchat API can not create a user's token")
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            url_service = rocket_chat_settings.get('public_url_service', None)

            data = response.get('data', {})

            auth_token = data.get('authToken', None)
            user_id = data.get('userId', None)

            subscriptions_rids = get_subscriptions_rids(auth_token, user_id, True)

            serializer = RocketChatCredentialsSerializer(
                data={"url_service": url_service, "auth_token": auth_token, "user_id": user_id, "room_ids": list(subscriptions_rids)}
            )
            serializer.is_valid()
            return Response(serializer.data, status=status.HTTP_200_OK)

        LOG.error("Rocketchat API object can not be initialized")
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RocketChatChangeRole(APIView):

    authentication_classes = (
        SessionAuthentication,
    )
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """
        This methods allows to chege the role of a specific user
        """
        if not request.user.is_staff:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        serializer = RocketChatChangeRoleSerializer(data=request.data)

        if not serializer.is_valid():
            return Response("Data is not valid", status=status.HTTP_400_BAD_REQUEST)

        username = serializer.data["username"]
        role = serializer.data["role"]

        rocket_chat_settings = get_rocket_chat_settings()

        api_rocket_chat = initialize_api_rocket_chat(rocket_chat_settings)

        if api_rocket_chat:

            user_info = api_rocket_chat.users_info(username=username)

            try:
                user_info = user_info.json()
                if not user_info.get('success', False):
                    return Response(user_info.get("error"), status=status.HTTP_400_BAD_REQUEST)

                user = user_info.get("user")
                data = {"roles": [role]}
                response = api_rocket_chat.users_update(user.get("_id"), **data)
                if response.status_code == 200:
                    return Response(status=status.HTTP_204_NO_CONTENT)
                return Response(response.json().get("error"), status=status.HTTP_400_BAD_REQUEST)

            except AttributeError:
                LOG.error("Rocketchat API can not get the user information")
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        LOG.error("Rocketchat API object can not be initialized")
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RocketChatCleanToken(APIView):

    authentication_classes = (
        SessionAuthentication,
    )
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        key = request.GET.get('beacon_rc')
        response = cache.get(key)

        if response:
            data = response.get('data', {})
            auth_token = data.get('authToken', None)
            user_id = data.get('userId', None)
            logout_status = logout(auth_token, user_id)

            if logout_status.get("status") == "success":
                cache.delete(key)
                return Response(status=status.HTTP_202_ACCEPTED)

        return Response(status=status.HTTP_401_UNAUTHORIZED)
