# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-04 02:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0072_attributetype_attribute_help_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='searchquery',
            name='parameters',
            field=models.TextField(),
        ),
    ]
