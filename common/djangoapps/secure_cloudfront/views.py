import logging
from datetime import datetime, timedelta

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect

from botocore.signers import CloudFrontSigner

LOGGER = logging.getLogger(__name__)


@login_required(redirect_field_name='dashboard')
def secure_cloudfront_video(request):
    """
    This view generates a redirect to the AWS resource
    """
    meta = request.META
    LOGGER.info('CloudFront view meta data = %s', meta)
    if not meta or meta.get('HTTP_HOST') not in meta.get('HTTP_REFERER', ''):
        raise Http404

    key = request.GET.get('key')

    if not key:
        raise Http404

    cloudfront_url = settings.CLOUDFRONT_URL
    cloudfront_id = settings.CLOUDFRONT_ID

    if not cloudfront_url or not cloudfront_id:
        raise Http404

    resource = '{}/{}'.format(cloudfront_url, key)

    expiration_date = _in_an_minute()

    cloudfront_signer = CloudFrontSigner(cloudfront_id, rsa_signer)
    redirect_url = cloudfront_signer.generate_presigned_url(resource, date_less_than=expiration_date)

    return redirect(redirect_url)


def rsa_signer(message):

    cloudfront_key = str(settings.CLOUDFRONT_PRIVATE_SIGNING_KEY)

    if not cloudfront_key:
        raise Http404

    private_key = serialization.load_pem_private_key(
        cloudfront_key,
        password=None,
        backend=default_backend()
    )
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())


def _in_an_minute():
    """
    """
    minute = timedelta(minutes=1)
    now = datetime.utcnow()
    return now + minute
