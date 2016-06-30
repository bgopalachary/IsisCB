# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-06-16 15:23
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0021_auto_20160616_1354'),
    ]

    operations = [
        migrations.CreateModel(
            name='DateRangeValue',
            fields=[
                ('value_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='isisdata.Value')),
                ('value', django.contrib.postgres.fields.ArrayField(base_field=models.DateField(), size=2)),
            ],
            options={
                'verbose_name': 'date range',
            },
            bases=('isisdata.value',),
        ),
    ]