# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('microsite_configuration', '0003_basicmicrosite'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalmicrositeorganizationmapping',
            name='history_user',
        ),
        migrations.RemoveField(
            model_name='historicalmicrositeorganizationmapping',
            name='microsite',
        ),
        migrations.RemoveField(
            model_name='historicalmicrositetemplate',
            name='history_user',
        ),
        migrations.RemoveField(
            model_name='historicalmicrositetemplate',
            name='microsite',
        ),
        migrations.DeleteModel(
            name='HistoricalMicrositeOrganizationMapping',
        ),
        migrations.DeleteModel(
            name='HistoricalMicrositeTemplate',
        ),
    ]
