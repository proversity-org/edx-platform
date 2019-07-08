"""
Base command to migrate contact id user values.
"""
from django.core.management.base import BaseCommand
from social_django.models import UserSocialAuth

from lms.djangoapps.student_account.models import UserSalesforceContactId


class Command(BaseCommand):
    """
    Command to migrate contact value from UserSocialAuth extra_data field to UserSalesforceContactId model.

    If a user has more than one contact id value it will take the most recent value to create the new record
    in the model UserSalesforceContactId.
    """
    help = """
        Migrate the contact id value from UserSocialAuth extra_data field to UserSalesforceContactId model,
        creating a new record for each user.
    """
    requires_migrations_checks = True


    def add_arguments(self, parser):
        """
        More info about add_arguments method:
        https://docs.djangoproject.com/en/1.11/howto/custom-management-commands/#django.core.management.BaseCommand.add_arguments
        """
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Show what records will be created without saving any records.',
        )


    def handle(self, *args, **options):
        """
        Creates a new record in the UserSalesforceContactId model from UserSocialAuth.
        Checks if the user record already exists, if so, it will be skipped.

        More info about handle method:
        https://docs.djangoproject.com/en/1.11/howto/custom-management-commands/#django.core.management.BaseCommand.handle
        """
        # reverse because we need the most recent value.
        all_social_users = UserSocialAuth.objects.all().reverse()

        for social_user in all_social_users:
            existing_contact_id = UserSalesforceContactId.objects.filter(
                user=social_user.user,
            )

            if existing_contact_id.exists():
                # Continue because we only need one record for each user.
                continue

            extra_data = getattr(social_user, 'extra_data', {})

            if not extra_data.get('contactid', False) or not getattr(social_user, 'provider', False):
                continue

            contact_id_source = 'sso:{}'.format(social_user.provider)
            user_contact_id = UserSalesforceContactId(
                user = social_user.user,
                contact_id = extra_data['contactid'],
                contact_id_source = contact_id_source,
            )

            if options.get('dry_run', False):
                self.stdout.write(success_created_message(user_contact_id))
            else:
                user_contact_id.save()
                self.stdout.write(success_created_message(user_contact_id))


def success_created_message(user_contact_id):
    """
    Util function to return the successful created record message.
    """
    return 'Created new record for user: {}, with Contact ID: {}, and source: {}.'.format(
        user_contact_id.user.email,
        user_contact_id.contact_id,
        user_contact_id.contact_id_source,
    )
