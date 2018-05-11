# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('user_api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RetirementState',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('state_name', models.CharField(unique=True, max_length=30)),
                ('state_execution_order', models.SmallIntegerField(unique=True)),
                ('is_dead_end_state', models.BooleanField(default=False, db_index=True)),
                ('required', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('state_execution_order',),
            },
        ),
        migrations.CreateModel(
            name='UserRetirementStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('original_username', models.CharField(max_length=150, db_index=True)),
                ('original_email', models.EmailField(max_length=254, db_index=True)),
                ('original_name', models.CharField(db_index=True, max_length=255, blank=True)),
                ('retired_username', models.CharField(max_length=150, db_index=True)),
                ('retired_email', models.EmailField(max_length=254, db_index=True)),
                ('responses', models.TextField()),
                ('current_state', models.ForeignKey(related_name='current_state', to='user_api.RetirementState')),
                ('last_state', models.ForeignKey(related_name='last_state', blank=True, to='user_api.RetirementState')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Retirement Status',
                'verbose_name_plural': 'User Retirement Statuses',
            },
        ),
    ]
