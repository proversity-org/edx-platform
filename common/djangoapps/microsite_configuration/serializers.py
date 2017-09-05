# serializers.py

from rest_framework import serializers
from microsite_configuration import models

class MicrositeSerializer(serializers.ModelSerializer):
    """ Serializes the BasicMicrosite object."""
    class Meta:
        model = models.BasicMicrosite
        fields = '__all__'

class MicrositeModelSerializer(serializers.ModelSerializer):
    """ Serializes the Microsite object."""
    class Meta(object): # pylint: disable=missing-docstring
       model = models.Microsite
       fields = '__all__'