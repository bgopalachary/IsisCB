# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('isisdata', '0033_auto_20160630_1845'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('administrator_notes', models.TextField(help_text=b'Curatorial discussion about the record.', null=True, blank=True)),
                ('record_history', models.TextField(help_text=b"Notes about the provenance of the information in this record. e.g. 'supplied by the author,' 'imported from SHOT bibliography,' 'generated by crawling UC Press website'", null=True, blank=True)),
                ('modified_on', models.DateTimeField(help_text=b'Date and time at which this object was last updated.', auto_now=True, null=True)),
                ('public', models.BooleanField(default=True, help_text=b'Controls whether this instance can be viewed by end users.')),
                ('record_status_value', models.CharField(blank=True, max_length=255, null=True, choices=[(b'Active', b'Active'), (b'Duplicate', b'Duplicate'), (b'Redirect', b'Redirect'), (b'Inactive', b'Inactive')])),
                ('record_status_explanation', models.CharField(max_length=255, null=True, blank=True)),
                ('created_on_fm', models.DateTimeField(help_text=b'Value of CreatedOn from the original FM database.', null=True)),
                ('created_by_fm', models.CharField(help_text=b'Value of CreatedBy from the original FM database.', max_length=255, null=True, blank=True)),
                ('modified_on_fm', models.DateTimeField(help_text=b'Value of ModifiedBy from the original FM database.', null=True, verbose_name=b'modified on (FM)')),
                ('modified_by_fm', models.CharField(help_text=b'Value of ModifiedOn from the original FM database.', max_length=255, verbose_name=b'modified by (FM)', blank=True)),
                ('dataset_literal', models.CharField(max_length=255, null=True, blank=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('modified_by', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text=b'The most recent user to modify this object.', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RenameField(
            model_name='aarelation',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='acrelation',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='attribute',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='authority',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='ccrelation',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='citation',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='historicalacrelation',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='historicalattribute',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='historicalauthority',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='historicalccrelation',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='historicalcitation',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='historicallinkeddata',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='historicalperson',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='historicaltracking',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='linkeddata',
            old_name='dataset',
            new_name='dataset_literal',
        ),
        migrations.RenameField(
            model_name='tracking',
            old_name='dataset',
            new_name='dataset_literal',
        ),
    ]