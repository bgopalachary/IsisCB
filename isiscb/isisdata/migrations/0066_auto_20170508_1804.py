# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-05-08 18:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0065_auto_20170508_1734'),
    ]

    operations = [
        migrations.AddField(
            model_name='citation',
            name='created_native',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='created_native',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
