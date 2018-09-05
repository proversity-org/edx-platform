
import json
import logging
import requests
import boto3

from datetime import datetime, timedelta
from email.utils import formatdate
from django.conf import settings
from django.core.urlresolvers import reverse

from lms.djangoapps.verify_student.ssencrypt import (
    generate_signed_message
)
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

log = logging.getLogger(__name__)

def get_houston_verify_student_settings():
    """
    Helper function to obtain VERIFY_STUDENT  setting for Houston Stu
    """
    VERIFY_STUDENT = settings.VERIFY_STUDENT["HOUSTON_STU"]
    VERIFY_STUDENT_MICROSITE = configuration_helpers.get_value(
        "VERIFY_STUDENT",
        settings.VERIFY_STUDENT
    )
    VERIFY_STUDENT_MICROSITE = VERIFY_STUDENT_MICROSITE["HOUSTON_STU"]
    VERIFY_STUDENT["HOUSTON_ORGANIZATION_ID"] = VERIFY_STUDENT_MICROSITE["HOUSTON_ORGANIZATION_ID"]
    VERIFY_STUDENT["HOUSTON_PROJECT_ID"] = VERIFY_STUDENT_MICROSITE["HOUSTON_PROJECT_ID"]
    VERIFY_STUDENT["API_ACCESS_KEY"] = VERIFY_STUDENT_MICROSITE["API_ACCESS_KEY"]
    VERIFY_STUDENT["API_SECRET_KEY"] = VERIFY_STUDENT_MICROSITE["API_SECRET_KEY"]
    
    return VERIFY_STUDENT

def create_houston_request(receipt_id, photo_id_key, user, copy_id_photo_from=None):
    """
    Construct the HTTP request to Houston Stu photo verification service.
    Keyword Arguments:
        copy_id_photo_from (SoftwareSecurePhotoVerification): If provided, re-send the ID photo
            data from this attempt.  This is used for reverification, in which new face photos
            are sent with previously-submitted ID photos.
    Returns:
        tuple of (header, body), where both `header` and `body` are dictionaries.
    """
    scheme = "https" if settings.HTTPS == "on" else "http"
    site_name = configuration_helpers.get_value('SITE_NAME', settings.SITE_NAME)
    callback_url = "{}://{}{}".format(
        scheme, site_name, reverse('verify_student_results_callback')
    )
    # If we're copying the photo ID image from a previous verification attempt,
    # then we need to send the old image data with the correct image key.
    VERIFY_STUDENT = get_houston_verify_student_settings()
    bucket = VERIFY_STUDENT["S3_BUCKET"]
    s3Client = boto3.client('s3', 
        aws_access_key_id=VERIFY_STUDENT["AWS_ACCESS_KEY"], 
        aws_secret_access_key=VERIFY_STUDENT["AWS_SECRET_KEY"], 
        region_name="us-east-1"
    )
    presigned_url_photo = s3Client.generate_presigned_url(
        'get_object',
        Params = {'Bucket': bucket, 'Key': 'face/{}'.format(receipt_id)},
        ExpiresIn = 600
    )
    presigned_url_id = s3Client.generate_presigned_url(
        'get_object',
        Params = {'Bucket': bucket, 'Key': 'photo_id/{}'.format(receipt_id)},
        ExpiresIn = 600
    )
    headers = {
        "Content-Type": "application/json",
        "Date": formatdate(timeval=None, localtime=False, usegmt=True)
    }
    houston_project_id = VERIFY_STUDENT["HOUSTON_PROJECT_ID"]
    houston_organisation_id = VERIFY_STUDENT["HOUSTON_ORGANIZATION_ID"]
    access_key = VERIFY_STUDENT["API_ACCESS_KEY"]
    secret_key = VERIFY_STUDENT["API_SECRET_KEY"]
    
    body_for_signature = {"EdX-ID": str(receipt_id)}
    _message, _sig, authorization = generate_signed_message(
        "POST", headers, body_for_signature, access_key, secret_key
    )
    headers['Authorization'] = authorization
    body = {
        "organisationId": houston_organisation_id,
        "projectId": houston_project_id,
        "preSignedUrlId": presigned_url_id,
        "preSignedUrlPhoto": presigned_url_photo,
        "photoId": str(receipt_id),
        "username": user.username,
        "email": user.email, 
        "callbackUrl": callback_url,
        "photoIdKey": photo_id_key
    }
    
    return headers, body
    
def send_houston_request(receipt_id, photo_id_key, user, copy_id_photo_from=None):
    """
    Assembles a submission to Houston Stu and sends it via HTTPS.
    Keyword Arguments:
        copy_id_photo_from (SoftwareSecurePhotoVerification): If provided, re-send the ID photo
            data from this attempt.  This is used for reverification, in which new face photos
            are sent with previously-submitted ID photos.
    Returns:
        request.Response
    """
    # If AUTOMATIC_VERIFY_STUDENT_IDENTITY_FOR_TESTING is True, we want to
    # skip posting anything to Houston Stu. We actually don't even
    # create the message because that would require encryption and message
    # signing that rely on settings.VERIFY_STUDENT values that aren't set
    # in dev. So we just pretend like we successfully posted

    if settings.FEATURES.get('AUTOMATIC_VERIFY_STUDENT_IDENTITY_FOR_TESTING'):
        fake_response = requests.Response()
        fake_response.status_code = 200
        return fake_response
    headers, body = create_houston_request(
        receipt_id, 
        photo_id_key,
        user,
        copy_id_photo_from=copy_id_photo_from
    )
    VERIFY_STUDENT = get_houston_verify_student_settings()
    response = requests.post(
        VERIFY_STUDENT["API_URL"],
        headers=headers,
        data=json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False).encode('utf-8'),
        verify=False
    )
    log.info("Sent request to Houston for receipt ID %s.", receipt_id)
    if copy_id_photo_from is not None:
        log.info(
            (
                "Houston Stu attempt with receipt ID %s used the same photo ID "
                "data as the receipt with ID %s"
            ),
            receipt_id, copy_id_photo_from.receipt_id
        )
    return response
