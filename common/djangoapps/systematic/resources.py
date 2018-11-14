import logging
from import_export import resources, fields
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from student.models import UserProfile


class UserResource(resources.ModelResource):

    password = fields.Field(attribute='password')

    # UserProfile columns
    name = fields.Field(attribute='name')
    gender = fields.Field(attribute='gender')
    city = fields.Field(attribute='city')
    year_of_birth = fields.Field(attribute='year_of_birth')
    level_of_education = fields.Field(attribute='level_of_education')

    class Meta:
        model = User
        import_id_fields = ['id']

        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'name',
            'gender',
            'city',
            'year_of_birth',
            'password',
            'date_joined',
            'level_of_education'
        )

        export_order = (
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
            'email',
            'name',
            'gender',
            'city',
            'year_of_birth',
            'date_joined',
            'level_of_education'
        )

    def before_save_instance(self, instance, using_transactions, dry_run):
        duplicate_email = False
        error_duplicate_email = 'Duplicate entry \'{}\' for key \'email\''.format(instance.email)

        if not instance.id:
            duplicate_email = User.objects.filter(email=instance.email).exists()
        elif instance.email and not instance.email == User.objects.get(id=instance.id).email:
            duplicate_email = User.objects.filter(email=instance.email).exists()

        if duplicate_email:
            raise Exception(error_duplicate_email)

        new_pass = ''

        if not instance.password:
            new_pass = '1234'
        elif type(instance.password) is int and str(instance.password)[-2:] == '.0':
            new_pass = str(instance.password)[:-2]
        else:
            new_pass = str(instance.password)

        instance.password = make_password(new_pass, salt=None, hasher='default')

    def after_save_instance(self, instance, using_transactions, dry_run):
        if not dry_run:
            try:
                userprofile, created_userprofile = UserProfile.objects.get_or_create(
                    user=instance,
                    defaults={
                        'name': instance.name,
                        'gender': instance.gender,
                        'year_of_birth': instance.year_of_birth,
                    }
                )

                if not created_userprofile:
                    userprofile.name = instance.name
                    userprofile.gender = instance.gender
                    userprofile.year_of_birth = instance.year_of_birth
                    userprofile.save()
            except Exception as e:
                logging.info(e)
