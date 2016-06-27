# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-06-15 16:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0019_auto_20160427_1520'),
    ]

    operations = [
        migrations.AddField(
            model_name='aarelation',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='aarelation',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='aarelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='personal_name_first',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='personal_name_last',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='personal_name_suffix',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='acrelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='attribute',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='attribute',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='attribute',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='attribute',
            name='type_qualifier',
            field=models.CharField(blank=True, choices=[(b'BGN', b'Began'), (b'END', b'Ended'), (b'OCR', b'Occurred')], max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='authority',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='authority',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='authority',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='ccrelation',
            name='data_display_order',
            field=models.FloatField(default=1.0, help_text=b'Position at which the citation should be displayed in the citation detail view. Whole numbers or decimals can be used.'),
        ),
        migrations.AddField(
            model_name='ccrelation',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='ccrelation',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='ccrelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='citation',
            name='additional_titles',
            field=models.TextField(blank=True, help_text=b'Additional titles (not delimited, free text).', null=True),
        ),
        migrations.AddField(
            model_name='citation',
            name='book_series',
            field=models.CharField(blank=True, help_text=b'Used for books, and potentially other works in a series.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='citation',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='citation',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='citation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='personal_name_first',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='personal_name_last',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='personal_name_suffix',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalacrelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalattribute',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalattribute',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalattribute',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalattribute',
            name='type_qualifier',
            field=models.CharField(blank=True, choices=[(b'BGN', b'Began'), (b'END', b'Ended'), (b'OCR', b'Occurred')], max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalauthority',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalccrelation',
            name='data_display_order',
            field=models.FloatField(default=1.0, help_text=b'Position at which the citation should be displayed in the citation detail view. Whole numbers or decimals can be used.'),
        ),
        migrations.AddField(
            model_name='historicalccrelation',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalccrelation',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalccrelation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='additional_titles',
            field=models.TextField(blank=True, help_text=b'Additional titles (not delimited, free text).', null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='book_series',
            field=models.CharField(blank=True, help_text=b'Used for books, and potentially other works in a series.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalcitation',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='access_status',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='access_status_date_verified',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='resource_name',
            field=models.CharField(blank=True, help_text=b'Name of the resource that the URN links to.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicallinkeddata',
            name='url',
            field=models.CharField(blank=True, help_text=b'If the resource has a DOI, use the DOI instead and do not include URL. Do include the http:// prefix. If used must also provide URLDateAccessed.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='personal_name_preferred',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicalperson',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicaltracking',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicaltracking',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicaltracking',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='access_status',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='access_status_date_verified',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='resource_name',
            field=models.CharField(blank=True, help_text=b'Name of the resource that the URN links to.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='linkeddata',
            name='url',
            field=models.CharField(blank=True, help_text=b'If the resource has a DOI, use the DOI instead and do not include URL. Do include the http:// prefix. If used must also provide URLDateAccessed.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='partdetails',
            name='extent',
            field=models.PositiveIntegerField(blank=True, help_text=b'Provides the size of the work in pages, words, or other counters.', null=True),
        ),
        migrations.AddField(
            model_name='partdetails',
            name='extent_note',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='personal_name_preferred',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='tracking',
            name='dataset',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='tracking',
            name='record_status_explanation',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='tracking',
            name='record_status_value',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
