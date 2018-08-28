import logging

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
)
from .serializers import RocketChatCredentialsSerializer

LOG = logging.getLogger(__name__)


class RocketChatCredentials(APIView):

    authentication_classes = (
        SessionAuthentication,
    )
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, course_id):
        """
        This returns a Json with the  user credentials in order to use the rocketchat api methods outside of the server
        """
        user = request.user

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

            response = api_rocket_chat.users_create_token(
                username=user.username)

            try:
                response = response.json()
            except AttributeError:
                LOG.error("Rocketchat API can not create a user's token")
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            url_service = rocket_chat_settings.get('public_url_service', None)

            data = response.get('data', {})

            auth_token = data.get('authToken', None)
            user_id = data.get('userId', None)

            subscriptions_rids = get_subscriptions_rids(api_rocket_chat, auth_token, user_id, True)

            serializer = RocketChatCredentialsSerializer(
                data={"url_service": url_service, "auth_token": auth_token, "user_id": user_id, "room_ids": list(subscriptions_rids)}
            )
            serializer.is_valid()
            return Response(serializer.data, status=status.HTTP_200_OK)

        LOG.error("Rocketchat API object can not be initialized")
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
