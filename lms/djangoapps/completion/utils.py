import logging
import pytz

from xmodule.modulestore.django import modulestore
from microsite_configuration import microsite
from student.models import get_user

from lms.djangoapps.completion.models import BlockCompletion
from lms.djangoapps.course_blocks.api import get_course_blocks
from lms.djangoapps.instructor_task.models import ReportStore

from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

CUSTOM_BLOCK_TYPES_KEY = "CUSTOM_BLOCK_TYPES"
REQUIRED_ACTIVITY_IDS_KEY = "REQUIRED_ACTIVITY_IDS"
logger = logging.getLogger(__name__)


class GenerateCompletionReport(object):

    def __init__(self, users, course_key, site_name=None):

        self.users = users
        self.course_key = course_key
        if site_name:
            microsite.set_by_domain(site_name)

    def generate_rows(self):
        """
        Returns a list with the headings and data for every user
        """
        rows = []

        fieldnames = ['full_name',
                      'user_id',
                      'username',
                      'email',
                      'first_login',
                      'last_login',
                      'days_since_last_login',
                      'completed_activities',
                      'total_program_activities'
                      ]

        required_ids = self.get_required_ids()

        for idx, item in enumerate(required_ids):
            fieldnames.append(" ".join(["required_activity", str(idx + 1)]))

        rows.append(fieldnames)

        for user in self.users:
            user, u_prof = get_user(user.email)
            completed_activities = self.get_completed_activities(user)
            activities = self.get_activities(user)
            last_login = user.last_login
            days_since_last_login = last_login.utcnow().replace(tzinfo=pytz.UTC) - last_login

            data = [u_prof.name,
                    user.id,
                    user.username,
                    user.email,
                    user.date_joined.strftime('%Y/%m/%d'),
                    last_login.strftime('%Y/%m/%d'),
                    days_since_last_login.days,
                    len(completed_activities),
                    len(activities)
                    ]

            for idx, item in enumerate(required_ids):
                state = "completed" if self.is_activity_completed(
                    item, completed_activities) else "not_completed"
                data.append(state)

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

        custom_block_types = configuration_helpers.get_value(CUSTOM_BLOCK_TYPES_KEY)

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
        return configuration_helpers.get_value(REQUIRED_ACTIVITY_IDS_KEY, [])

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
