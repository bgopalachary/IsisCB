# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-07-11 04:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0024_auto_20180709_0216'),
    ]

    operations = [
        migrations.AddField(
            model_name='importaccession',
            name='import_errors',
            field=models.TextField(blank=True, null=True),
        ),
    ]
