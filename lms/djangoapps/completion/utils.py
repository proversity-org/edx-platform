import logging

from opaque_keys.edx.locator import BlockUsageLocator
from student.models import get_user
from social_django.models import UserSocialAuth
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError

from lms.djangoapps.completion.models import BlockCompletion
from lms.djangoapps.course_blocks.api import get_course_blocks
from lms.djangoapps.courseware.courses import get_course_by_id
from lms.djangoapps.instructor_task.models import ReportStore


logger = logging.getLogger(__name__)


class GenerateCompletionReport(object):

    def __init__(self, users, course_key):

        self.users = users
        self.course_key = course_key
        self.course = get_course_by_id(self.course_key)

    def generate_rows(self):
        """
        Returns a list with the headings and data for every user
        """

        def get_contact_id(user):
            contact_ids = [
                social_auth.extra_data.get("contactid")
                for social_auth in UserSocialAuth.get_social_auth_for_user(user)
                if social_auth.provider == "tpa-saml"
            ]
            first_id = next(iter(contact_ids), None)

            if isinstance(first_id, list):
                return next(iter(first_id), None)
            return first_id

        rows = []

        fieldnames = [
            'First Name',
            'Last Name',
            'Student Enrollment ID',
            'Email',
            'First Login',
            'Last Login',
            'Completed Activities',
            'Total Activities',
            'Module Code',
            'ContactID 18',
        ]

        required_ids = self.get_required_ids()
        activities = len(required_ids)

        for idx, item in enumerate(required_ids):
            fieldnames.append("Required Activity {} ".format(idx + 1))
            fieldnames.append("Required Activity {} Name".format(idx + 1))

        rows.append(fieldnames)

        for user in self.users:
            user, user_profile = get_user(user.email)
            first_name, last_name = self.get_first_and_last_name(user_profile.name)
            completed_activities = self.get_completed_activities(user)
            last_login = user.last_login
            display_last_login = None
            # Last login could not be defined for a user
            if last_login:
                display_last_login = last_login.strftime('%Y/%m/%d %H:%M:%S')

            student_enrollment_id = "{org}-{user_id}".format(org=self.course_key.org, user_id=user.id)

            data = [
                first_name,
                last_name,
                student_enrollment_id,
                user.email,
                user.date_joined.strftime('%Y/%m/%d %H:%M:%S'),
                display_last_login,
                self.get_count_required_completed_activities(required_ids, completed_activities),
                activities,
                self.course_key.to_deprecated_string(),
                get_contact_id(user),
            ]

            for id in required_ids:
                block_type, block_id = id.rsplit("+block@")
                state = "completed" if self.is_activity_completed(
                    block_id, completed_activities) else "not_completed"
                data.append(state)
                locator = BlockUsageLocator(self.course_key, block_type, block_id)

                try:
                    block = modulestore().get_item(locator)
                except ItemNotFoundError as item_error:
                    logger.warn(
                        "The block type %s with id %s is not valid, error: %s",
                        block_type,
                        block_id,
                        item_error
                    )
                    continue
                data.append(block.display_name)

            rows.append(data)

        return rows

    def get_activities(self, user):
        """
        Return the avalaible activities on the course
        """
        usage_key = modulestore().make_course_usage_key(self.course_key)
        blocks = get_course_blocks(user, usage_key)

        block_types_filter = [
            'html',
            'problem',
            'video',
            'discussion',
        ]

        custom_block_types = self.course.custom_block_type_keys

        if custom_block_types:
            for block_type in custom_block_types:
                block_types_filter.append(block_type)

        # filter blocks by types
        if block_types_filter:
            block_keys_to_remove = []
            for block_key in blocks:
                block_type = blocks.get_xblock_field(block_key, 'category')
                if block_type not in block_types_filter:
                    block_keys_to_remove.append(block_key)
            for block_key in block_keys_to_remove:
                blocks.remove_block(block_key, keep_descendants=True)

        return blocks

    def get_completed_activities(self, user):
        """
        Return blocks that have been completed by the user
        """
        return BlockCompletion.get_course_completions(user, self.course_key)

    def get_required_ids(self):
        """
        This get the ids for the required activities
        """
        return self.course.required_activity_ids

    def is_activity_completed(self, id, activities):
        """
        Verify if the id exist for the given activity list
        """
        for activity in activities:
            if id == activity.block_id:
                return True
        return False

    def store_report(self, rows):
        """
        Store a CVS file with the data in rows
        """
        config_name = "COMPLETION_DOWNLOAD"
        report_store = ReportStore.from_config(config_name)
        report_store.store_rows(self.course_key, "completion_data.csv", rows)
        return report_store.links_for(self.course_key)[0][1]

    @staticmethod
    def serialize_rows(rows):
        headers = rows.pop(0)
        return [dict(zip(headers, row)) for row in rows]

    def get_count_required_completed_activities(self, required_ids, activities):
        """
        Returns a counter with the number of required activities defined on studio
        """
        count = 0
        for id in required_ids:
            block_type, block_id = id.rsplit("+block@")
            for activity in activities:
                if block_id == activity.block_id:
                    count += 1

        return count

    def get_first_and_last_name(self, full_name):
        """
        Takes the argument full_name a returns a list with the first name and last name
        """
        try:
            result = full_name.split(' ', 1)
        except AttributeError:
            return ['', '']
        else:
            if len(result) == 2:
                return result
            return [full_name, full_name]
