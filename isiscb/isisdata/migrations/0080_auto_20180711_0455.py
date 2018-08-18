# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-07-11 04:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0079_auto_20180629_0247'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalacrelation',
            name='history_change_reason',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='historicalattribute',
            name='history_change_reason',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='history_change_reason',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='historicalauthoritytracking',
            name='history_change_reason',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='historicalccrelation',
            name='history_change_reason',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='history_change_reason',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='history_change_reason',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='history_change_reason',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='historicaltracking',
            name='history_change_reason',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='authority',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update'), (b'NO', b'No')], max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update'), (b'NO', b'No')], max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update'), (b'NO', b'No')], max_length=2, null=True),
        ),
    ]