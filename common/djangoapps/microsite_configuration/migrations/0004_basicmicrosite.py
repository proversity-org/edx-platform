# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('microsite_configuration', '0003_delete_historical_records'),
    ]

    operations = [
        migrations.CreateModel(
            name='BasicMicrosite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('values', jsonfield.fields.JSONField(blank=True)),
            ],
        ),
    ]
