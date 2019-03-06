# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ReportsStatus',
            fields=[
                ('jobid', models.CharField(max_length=255, serialize=False, primary_key=True, db_index=True)),
                ('status', models.CharField(max_length=15, choices=[(1, b'Running'), (2, b'Finished')])),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('result', models.TextField(null=True)),
            ],
            options={
                'db_table': 'reports_status',
            },
        ),
    ]
