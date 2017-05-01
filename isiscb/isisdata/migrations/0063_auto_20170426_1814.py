# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-26 18:14
from __future__ import unicode_literals

from django.db import migrations

stages = ['BD', 'FU', 'PD', 'AU', 'HS', 'PT']


def set_citation_tracking_state(apps, schema_editor):
    from collections import OrderedDict
    Tracking = apps.get_model("isisdata", "Tracking")
    Citation = apps.get_model("isisdata", "Citation")


    N = Citation.objects.all().count()
    for i, citation in enumerate(Citation.objects.all()):
        # print '\r', 100*float(i)/N, '%',
        tracking_types = list(citation.tracking_records.all().values_list('type_controlled', flat=True))
        for stage in stages[::-1]:
            if stage in tracking_types:
                citation.tracking_state = stage
                citation.save()
                break


def set_authority_tracking_state(apps, schema_editor):
    from collections import OrderedDict
    AuthorityTracking = apps.get_model("isisdata", "AuthorityTracking")
    Authority = apps.get_model("isisdata", "Authority")
    ContentType = apps.get_model("contenttypes", "ContentType")

    N = Authority.objects.all().count()
    for i, authority in enumerate(Authority.objects.all()):
        # print '\r', 100*float(i)/N, '%',
        tracking_types = list(authority.tracking_records.all().values_list('type_controlled', flat=True))
        for stage in stages[::-1]:
            if stage in tracking_types:
                authority.tracking_state = stage
                authority.save()
                break
        # sys.stdout.flush()


def clear_citation_tracking_state(apps, schema_editor):
    pass


def clear_authority_tracking_state(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('isisdata', '0062_auto_20170426_1813'),
    ]

    operations = [
        migrations.RunPython(set_citation_tracking_state, clear_citation_tracking_state),
        migrations.RunPython(set_authority_tracking_state, clear_authority_tracking_state),
    ]
