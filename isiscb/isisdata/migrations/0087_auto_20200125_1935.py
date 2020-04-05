# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-01-25 19:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0086_auto_20200112_2037'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authority',
            name='classification_system',
            field=models.CharField(blank=True, choices=[(b'SPWT', b'Weldon Thesaurus Terms (2002-present)'), (b'SPWC', b'Weldon Classification System (2002-present)'), (b'GUE', b'Guerlac Committee Classification System (1953-2001)'), (b'NEU', b'Neu'), (b'MW', b'Whitrow Classification System (1913-1999)'), (b'SHOT', b'SHOT Thesaurus Terms'), (b'FHSA', b'Forum for the History of Science in America'), (b'SAC', b'Search App Concept'), (b'PN', b'Proper name')], db_index=True, default=b'SPWC', help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', max_length=4, null=True),
        ),
        migrations.AlterField(
            model_name='authority',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update'), (b'NO', b'No')], db_index=True, max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name='authority',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[(b'PE', b'Person'), (b'IN', b'Institution'), (b'TI', b'Time Period'), (b'GE', b'Geographic Term'), (b'SE', b'Serial Publication'), (b'CT', b'Classification Term'), (b'CO', b'Concept'), (b'CW', b'Creative Work'), (b'EV', b'Event'), (b'CR', b'Cross-reference')], db_index=True, help_text=b'Specifies authority type. Each authority thema has its own list of controlled type vocabulary.', max_length=2, null=True, verbose_name=b'type'),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='classification_system',
            field=models.CharField(blank=True, choices=[(b'SPWT', b'Weldon Thesaurus Terms (2002-present)'), (b'SPWC', b'Weldon Classification System (2002-present)'), (b'GUE', b'Guerlac Committee Classification System (1953-2001)'), (b'NEU', b'Neu'), (b'MW', b'Whitrow Classification System (1913-1999)'), (b'SHOT', b'SHOT Thesaurus Terms'), (b'FHSA', b'Forum for the History of Science in America'), (b'SAC', b'Search App Concept'), (b'PN', b'Proper name')], db_index=True, default=b'SPWC', help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', max_length=4, null=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update'), (b'NO', b'No')], db_index=True, max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name='historicalauthority',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[(b'PE', b'Person'), (b'IN', b'Institution'), (b'TI', b'Time Period'), (b'GE', b'Geographic Term'), (b'SE', b'Serial Publication'), (b'CT', b'Classification Term'), (b'CO', b'Concept'), (b'CW', b'Creative Work'), (b'EV', b'Event'), (b'CR', b'Cross-reference')], db_index=True, help_text=b'Specifies authority type. Each authority thema has its own list of controlled type vocabulary.', max_length=2, null=True, verbose_name=b'type'),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='classification_system',
            field=models.CharField(blank=True, choices=[(b'SPWT', b'Weldon Thesaurus Terms (2002-present)'), (b'SPWC', b'Weldon Classification System (2002-present)'), (b'GUE', b'Guerlac Committee Classification System (1953-2001)'), (b'NEU', b'Neu'), (b'MW', b'Whitrow Classification System (1913-1999)'), (b'SHOT', b'SHOT Thesaurus Terms'), (b'FHSA', b'Forum for the History of Science in America'), (b'SAC', b'Search App Concept'), (b'PN', b'Proper name')], db_index=True, default=b'SPWC', help_text=b'Specifies the classification system that is the source of the authority. Used to group resources by the Classification system. The system used currently is the Weldon System. All the other ones are for reference or archival purposes only.', max_length=4, null=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='tracking_state',
            field=models.CharField(blank=True, choices=[(b'HS', b'HSTM Upload'), (b'PT', b'Printed'), (b'AU', b'Authorized'), (b'PD', b'Proofed'), (b'FU', b'Fully Entered'), (b'BD', b'Bulk Data Update'), (b'NO', b'No')], db_index=True, max_length=2, null=True),
        ),
        migrations.AlterField(
            model_name='historicalperson',
            name='type_controlled',
            field=models.CharField(blank=True, choices=[(b'PE', b'Person'), (b'IN', b'Institution'), (b'TI', b'Time Period'), (b'GE', b'Geographic Term'), (b'SE', b'Serial Publication'), (b'CT', b'Classification Term'), (b'CO', b'Concept'), (b'CW', b'Creative Work'), (b'EV', b'Event'), (b'CR', b'Cross-reference')], db_index=True, help_text=b'Specifies authority type. Each authority thema has its own list of controlled type vocabulary.', max_length=2, null=True, verbose_name=b'type'),
        ),
    ]