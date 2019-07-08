"""
Student account custom models.
"""

from django.contrib.auth.models import User
from django.db import models


class UserSalesforceContactId(models.Model):
    """
    Model to track the Salesforce Contact ID 18 user value.

    The field contact id is unique for each user.

    The user contact id was initially stored in the model UserSocialAuth extra_data.

    A new Django command is available to grab the user contact id from UserSocialAuth
    and then create the new record in this model.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    contact_id = models.CharField(max_length=60)
    contact_id_source = models.CharField(max_length=60)
