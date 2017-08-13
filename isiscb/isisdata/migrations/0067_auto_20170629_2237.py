# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-06-29 22:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0066_auto_20170508_1804'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authority',
            name='name',
            field=models.CharField(db_index=True, help_text=b'Name, title, or other main term for the authority as will be displayed.', max_length=1000),
        ),
        migrations.AlterField(
            model_name='authority',
            name='name_for_sort',
            field=models.CharField(blank=True, db_index=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='name',
            field=models.CharField(db_index=True, help_text=b'Name, title, or other main term for the authority as will be displayed.', max_length=1000),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='name_for_sort',
            field=models.CharField(blank=True, db_index=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='name',
            field=models.CharField(db_index=True, help_text=b'Name, title, or other main term for the authority as will be displayed.', max_length=1000),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='name_for_sort',
            field=models.CharField(blank=True, db_index=True, max_length=2000, null=True),
        ),
    ]