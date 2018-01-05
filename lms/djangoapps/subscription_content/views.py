""" Subscription content views. """

import logging
from django.conf import settings
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from student.cookies import set_user_info_cookie
from edxmako.shortcuts import render_to_response

from api import get_access_token, get_catalogues, get_content_items, get_content_item
from helpers import get_subscription_catalog_ids

log = logging.getLogger(__name__)

@login_required
@ensure_csrf_cookie
def dashboard(request):
  context = {}
  client_id =  configuration_helpers.get_value('BIBBLIO_CLIENT_ID', settings.BIBBLIO_CLIENT_ID)
  client_secret =  configuration_helpers.get_value('BIBBLIO_CLIENT_SECRET', settings.BIBBLIO_CLIENT_SECRET)
  token = get_access_token(client_id, client_secret)
  if 'access_token' in token:
    catalog_ids = get_subscription_catalog_ids(request.user)
    if catalog_ids:
      context = { 'message': '', 'content_items': {} }
      content_items = get_content_items(token['access_token'], catalog_ids)
      if 'results'in content_items:
        for item in content_items['results']:
          context['content_items'][item['contentItemId']] = item
          content_item = get_content_item(token['access_token'], item['contentItemId'])
          if 'contentItemId' in content_item:
            if not content_item['thumbnail'] and content_item['moduleImage']:
              content_item['thumbnail'] = content_item['moduleImage']
            context['content_items'][item['contentItemId']]['meta'] = content_item
          else:
            context['message'] = context['message']+"<br />"+item['name']+": "+content_item['message']
      else:
        context['message'] = context['message']+"<br />"+content_items['message']
    else:
      context = { 'message': token['message'] }

  response = render_to_response('subscription_content/dashboard.html', context)
  set_user_info_cookie(response, request)
  return response


def catalogues(request):
  token = get_access_token(client_id, client_secret)
  if 'access_token' in token:
    context = { 'message': '', 'catalogues': {} }
    catalogues = get_catalogues(token['access_token'])
    if 'results' in catalogues:
      for catalogue in catalogues['results']:
        context['catalogues'][catalogue['catalogueId']] = catalogue
    else:
      context['message'] = context['message']+"<br />"+catalogues['message']
  else:
    context = { 'message': token['message'] }

  response = render_to_response('subscription_content/all.html', context)
  set_user_info_cookie(response, request)
  return response