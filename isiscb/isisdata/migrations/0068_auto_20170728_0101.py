# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-07-28 01:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0067_auto_20170629_2237'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='bio_markup_type',
            field=models.CharField(choices=[(b'', b'--'), (b'html', 'HTML'), (b'plain', 'Plain'), (b'markdown', 'Markdown'), (b'restructuredtext', 'Restructured Text')], default=b'markdown', editable=False, max_length=30),
        ),
    ]
