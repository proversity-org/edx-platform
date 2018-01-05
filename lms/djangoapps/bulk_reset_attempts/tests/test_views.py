"""
Tests for the Bulk Enrollment views.
"""
import ddt
import json

from django.core.urlresolvers import reverse

from rest_framework.test import \
    APIRequestFactory, APITestCase, force_authenticate

from bulk_reset_attempts.serializers import BulkResetStudentAttemptsSerializer
from bulk_reset_attempts.views import BulkResetStudentAttemptsView

from student.tests.factories import UserFactory

from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


@ddt.ddt
class BulkResetStudentAttemptsViewTest(SharedModuleStoreTestCase, APITestCase):
    """
    Test the bulk reset attempts endpoint
    """

    USERNAME = "Bob"
    EMAIL = "bob@example.com"
    PASSWORD = "edx"

    @classmethod
    def setUpClass(cls):
        super(BulkResetStudentAttemptsViewTest, cls).setUpClass()

        cls.course =\
            CourseFactory.create(
                display_name='Read My Mind',
                run="2017",
                org="KIL",
                number="KIL001"
            )

    def setUp(self):
        super(BulkResetStudentAttemptsViewTest, self).setUp()

        self.view = BulkResetStudentAttemptsView.as_view()
        self.request_factory = APIRequestFactory()
        self.url = reverse('bulk_reset_student_attempts')

        self.staff = UserFactory.create(
            username=self.USERNAME,
            email=self.EMAIL,
            password=self.PASSWORD,
            is_staff=True,
        )

    def request_bulk_reset_attempts(self, data=None, use_json=False, **extra):
        """ Make an authenticated request to the bulk enrollment API. """
        content_type = None
        if use_json:
            content_type = 'application/json'
            data = json.dumps(data)
        request = self.request_factory.post(
            self.url,
            data=data,
            content_type=content_type,
            **extra
        )
        force_authenticate(request, user=self.staff)
        response = self.view(request)
        response.render()
        return response

    @ddt.data(
        (dict(
            course_id="course-v1:KIL+KIL001+2017",
            identifiers="staff",
            problems="")
        ),
        (dict(
            course_id="course-v1:KIL+KIL001+2017",
            identifiers="staff",
            problems="problem_id")
        ),
        (dict(
            course_id="course-v1:KIL+KIL001+2017",
            identifiers="",
            problems="problem_id")
        ),
        (dict(
            course_id="course-v1:KIL+KIL001+2017",
            identifiers="staff",
            problems="",
            email_extension="@example.com")
        ),
        (dict(
            course_id="course-v1:KIL+KIL001+2017",
            identifiers="",
            problems="problem_id",
            email_extension="@example.com")
        ),
        (dict(
            course_id="course-v1:KIL+KIL001+2017",
            identifiers="staff",
            problems="problem_id",
            email_extension="@example.com")
        ),
    )
    def test_serializer(self, data):
        """ Test that passing valid data the serializer works. """
        serializer = BulkResetStudentAttemptsSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_non_staff(self):
        """ Test that non global staff users are forbidden from API use. """
        self.staff.is_staff = False
        self.staff.save()
        response = self.request_bulk_reset_attempts()
        self.assertEqual(response.status_code, 403)

    @ddt.data(
        (
            dict(),
            dict(
                course_id=["This field is required."],
                identifiers=["This field is required."],
                problems=["This field is required."]
            )
        ),
        (
            dict(identifiers="", problems=""),
            dict(course_id=["This field is required."])
        ),
        (
            dict(course_id="course-v1:KIL+KIL001+2017", problems=""),
            dict(identifiers=["This field is required."])
        ),
        (
            dict(course_id="course-v1:KIL+KIL001+2017", identifiers=""),
            dict(problems=["This field is required."])
        ),
    )
    @ddt.unpack
    def test_missing_data(self, data, error):
        """ Test that we are not passing the required fields. """
        response = self.request_bulk_reset_attempts(data, use_json=True)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), error)

    @ddt.data(
        (
            dict(
                course_id="course-v1:edX",
                identifiers="",
                problems=""
            ),
            dict(error="Invalid course id: 'course-v1:edX'")
        ),
    )
    @ddt.unpack
    def test_wrong_course_id(self, data, error):
        """ Test that we are passing an invalid course id. """
        response = self.request_bulk_reset_attempts(data, use_json=True)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), error)

    @ddt.data(
        (
            dict(
                course_id="course-v1:KIL+KIL001+2017",
                identifiers="user1, user2, user3",
                problems=""
            ),
            dict(
                user1="User does not exist",
                user2="User does not exist",
                user3="User does not exist"
            )
        ),
    )
    @ddt.unpack
    def test_user_does_not_exist(self, data, error):
        """ Test that we are passing users that don't exists. """
        response = self.request_bulk_reset_attempts(data, use_json=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["errors"], error)

    @ddt.data(
        (
            dict(
                course_id="course-v1:KIL+KIL001+2017",
                identifiers="Bob",
                problems="problem_id"
            ),
            dict(problem_id="The problem does not exist")
        ),
    )
    @ddt.unpack
    def test_problem_does_not_exist(self, data, error):
        """ Test that we are passing problems that don't exists. """
        response = self.request_bulk_reset_attempts(data, use_json=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["errors"], error)
