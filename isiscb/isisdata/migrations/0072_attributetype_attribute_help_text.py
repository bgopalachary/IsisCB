# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-10-30 00:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0071_asynctask_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='attributetype',
            name='attribute_help_text',
            field=models.TextField(blank=True, default=None, help_text=b'The help text the user sees when adding a new attribute of this type.', null=True),
        ),
    ]
