# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-24 16:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0014_auto_20160422_1509'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partdetails',
            name='issue_free_text',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='partdetails',
            name='pages_free_text',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='partdetails',
            name='volume',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='partdetails',
            name='volume_free_text',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
