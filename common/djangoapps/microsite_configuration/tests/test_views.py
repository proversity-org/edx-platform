'''
    Tests for Microsites API views
'''
import json
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from microsite_configuration.tests.factories import MicrositeFactory
from microsite_configuration.models import Microsite

class TestMicrositesViewSet(TestCase):

    '''
        Test suit for microsites api views.
    '''

    def setUp(self):
        '''
            Define the test client and other test variables
        '''
        user = User.objects.create(username="testUser")

        # Initialize client and force it to use authentication
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_authenticate(user=user)
        self.microsite = MicrositeFactory.create()
        # Create microsite in the setup, create some microsites

    def test_api_can_get_microsite_list(self):
        '''
            Test that the api can get a microsite
        '''
        response = self.client.get(reverse('microsites-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_api_can_create_microsite(self):
        '''
            Test that the api can create a microsite
        '''
        my_test_data = {
            "domain_prefix": "test-site",
            "university": "test_site", "platform_name": "Test Site DB",
            "logo_image_url": "test_site/images/header-logo.png",
            "email_from_address": "test_site@edx.org",
            "payment_support_email": "test_site_dbe@edx.org",
            "ENABLE_MKTG_SITE": "false",
            "SITE_NAME": "test_site.localhost",
            "course_org_filter": "TestSiteX",
            "course_about_show_social_links": "false",
            "css_overrides_file": "test_site/css/test_site.css",
            "show_partners": "false",
            "show_homepage_promo_video": "false",
            "course_index_overlay_text": "This is a Test Site Overlay Text.",
            "course_index_overlay_logo_file": "test_site/images/header-logo.png",
            "homepage_overlay_html": "<h1>This is a Test Site Overlay HTML</h1>"
        }
        response = self.client.post(
            reverse('microsites-list'),
            my_test_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_authentication_is_enforced(self):
        '''
            Test that the API user is authenticated
        '''
        new_client = APIClient()
        response = new_client.get('/api/microsites/v1/microsites/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)



class TestMicrositesDetailView(TestCase):
    '''
     Test for MicrsitesDeatailView
    '''

    def setUp(self):

        user = User.objects.create(username="nerd")
        # Initialize client and force it to use authentication
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        self.microsite = MicrositeFactory.create()
        self.valid_payload = {
            "domain_prefix": "staging.ttro",
            "SITE_NAME": "staging.ttro.proversity.io",
            "platform_name": "Test Site DB",
            "course_org_filter": "test_site",
            "show_homepage_promo_video": 'false',
            "course_about_show_social_links": 'false',
            "css_overrides_file": "TTR/css/overrides.css",
            "favicon_path": "TTR/images/favicon.ico",
            "ENABLE_MKTG_URLS": 'false'
        }

        self.invalid_payload = {
            "domain_prefix": "staging.ttro",
            "SITE_NAME": "staging.ttro.proversity.io",
            "platform_name": "Test Site DB",
            "course_org_filter": "TestSiteX", #Can never change the org code
            "show_homepage_promo_video": 'false',
            "course_about_show_social_links": 'false',
            "css_overrides_file": "TTR/css/overrides.css",
            "favicon_path": "TTR/images/favicon.ico",
            "ENABLE_MKTG_URLS": 'false'
        }

    def test_api_can_get_a_microsite(self):
        '''
            Test that the api can get a microsite
        '''
        url = reverse('microsite-detail', kwargs={"pk": 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_does_not_get_invalid_microsite(self):
        '''
            Test that the api can get a microsite
        '''
        url = reverse('microsite-detail', kwargs={"pk": 1000})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_api_can_update_microsite(self):
        '''
            Test that the api can update a microsite
        '''
        url = reverse('microsite-detail', kwargs={"pk": 1})
        response = self.client.put(
            url,
            data=json.dumps(self.valid_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_can_delete_microsite(self):
        '''
            Test that the api can delete a micrdosite
        '''
        url = reverse('microsite-detail', kwargs={"pk": 1})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertRaises(Microsite.DoesNotExist):
            Microsite.objects.get(pk=1)


    def test_api_invalid_update_microsite(self):

        '''
            Test that update doesn't work when microsite doesn't exist
        '''
        url = reverse('microsite-detail', kwargs={"pk": 1})
        response = self.client.put(
            url,
            data=self.invalid_payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
