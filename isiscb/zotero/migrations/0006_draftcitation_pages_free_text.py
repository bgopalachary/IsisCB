# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-27 15:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zotero', '0005_auto_20160425_1334'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftcitation',
            name='pages_free_text',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]