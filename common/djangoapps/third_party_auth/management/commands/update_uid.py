"""
Base command to update the uid value on the in the UserSocialAuth table.
"""
from django.db import transaction
from django.core.management.base import CommandError
from social_django.models import UserSocialAuth

from track.management.tracked_command import TrackedCommand


class Command(TrackedCommand):
    """
    This command allows to update the uid using a value from the extra_data field
    for a given provider.

    If the given field doesn't exist, an exception will be raised and the process
    won't finish.
    """
    help = """
    This command updates all the uid fields in the UserSocialAuth table
    taking a specific data from the extra_data field.

    example:
        manage.py ... update_uid google-oauth2 salesforceid
    """

    def add_arguments(self, parser):
        parser.add_argument('provider')
        parser.add_argument('field')

    @transaction.atomic
    def handle(self, provider, field, *args, **kwargs):
        """
        Get all the objects for the given provider and update the uid.
        """
        user_social_auth_registers = UserSocialAuth.objects.filter(provider=provider)

        for user_social_auth_register in user_social_auth_registers:
            new_uid = user_social_auth_register.extra_data.get(field)

            if not new_uid:
                raise CommandError('There is no field {} in the extra_data field.'.format(field))

            user_social_auth_register.uid = new_uid
            user_social_auth_register.save()

        self.stdout.write('All the objects for {} have been updated successfully.'.format(provider))
