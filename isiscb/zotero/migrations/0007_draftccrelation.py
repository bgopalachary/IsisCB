# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-27 19:59
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('zotero', '0006_draftcitation_pages_free_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='DraftCCRelation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imported_on', models.DateTimeField(auto_now_add=True)),
                ('processed', models.BooleanField(default=False, help_text='Indicates whether or not a record has been inspected, and a corresponding entry/entries in isisdata have been created. When True, a record should be hidden from the curation interface by default.')),
                ('name', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True)),
                ('type_controlled', models.CharField(blank=True, choices=[('IC', 'Includes Chapter'), ('ISA', 'Includes Series Article'), ('RO', 'Is Review Of'), ('RE', 'Responds To'), ('AS', 'Is Associated With'), ('RB', 'Is Reviewed By')], max_length=3, null=True)),
                ('type_free', models.CharField(blank=True, max_length=255, null=True)),
                ('imported_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('object', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relations_to', to='zotero.DraftCitation')),
                ('part_of', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='zotero.ImportAccession')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relations_from', to='zotero.DraftCitation')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]