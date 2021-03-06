# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-06-29 02:47
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('isisdata', '0078_auto_20180623_0200'),
    ]

    operations = [
        migrations.AddField(
            model_name='authority',
            name='created_by_stored',
            field=models.ForeignKey(blank=True, help_text=b'The user who created this object.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='creator_of_object', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='authority',
            name='created_on_stored',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='created_by_stored',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='created_on_stored',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='created_by_stored',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='created_on_stored',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
