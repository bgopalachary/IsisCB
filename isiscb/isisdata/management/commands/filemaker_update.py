from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import zip
from builtins import object
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist, FieldError, ValidationError
from django.contrib.contenttypes.models import ContentType
from django.db.utils import IntegrityError
from isisdata.models import *

import datetime, iso8601, string
import xml.etree.ElementTree as ET
import os
import copy
import json
import re
import pprint

from collections import Counter

def _update_or_create(model, pk, data):
    try:
        instance = model.objects.get(pk=pk)
        for key, value in list(data.items()):
            if key == 'id':
                pass
            setattr(instance, key, value)
        instance.save()
    except model.DoesNotExist:
        instance = model.objects.create(**data)
        for key, value in list(data.items()):
            print(key, value)
            if getattr(instance, key) != value:
                setattr(instance, key, value)
        instance.save()

    return instance


with open('isisdata/fixtures/language.json', 'r') as f:
    languages = json.load(f)
languageLookup = {l['fields']['name'].lower(): l['pk'] for l in languages}
languageLookup.update({l['pk'].lower(): l['pk'] for l in languages})


def fast_iter(context, func, tag, *extra):
    for event, elem in context:
        func(elem, *extra)
        if elem.tag.replace('{http://www.filemaker.com/fmpdsoresult}', '') == tag:
            elem.clear()
    del context


def _strip_non_numbers(s):
    transmap = string.maketrans('','')
    nodigs = transmap.translate(transmap, string.digits)
    return s.translate(transmap, nodigs)


class FMPDSOParser(object):
    """
    Parses FileMaker's FMPDSO XML format into field-data that can be ingested
    into the IsisCB Explore ORM.
    """
    fm_namespace = '{http://www.filemaker.com/fmpdsoresult}'
    datetime_formats = [
        '%m/%d/%Y %I:%M:%S %p',
        '%m/%d/%Y %I:%M %p'
    ]
    date_formats = [
        '%m/%d/%Y',
        '%Y'
    ]
    chunk_size = 10000  # Number of instances to include in each fixture file.
    as_int = lambda x: int(x)
    as_upper = lambda x: x.upper()

    @staticmethod
    def _as_datetime(model_name, fm_field, fm_value):
        """
        Attempt to coerce a value to ``datetime``.
        """
        if len(fm_value) < 4:
            fm_value = string.zfill(fm_value, 4)

        for format in FMPDSOParser.datetime_formats + FMPDSOParser.date_formats:
            try:
                return datetime.datetime.strptime(fm_value, format)
            except ValueError:
                pass
        try:
            return iso8601.parse_date(fm_value)
        except ValueError:
            pass
        raise ValueError('Could not coerce value to datetime: %s' % fm_value)

    @staticmethod
    def _to_int(model_name, fm_field, fm_value):
        try:
            return int(fm_value)
        except TypeError:
            return 1

    @staticmethod
    def _to_float(model_name, fm_field, fm_value):
        return float(fm_value)

    @staticmethod
    def _to_date(model_name, fm_field, fm_value):
        return FMPDSOParser._as_datetime(model_name, fm_field, fm_value).date()

    @staticmethod
    def _try_int(model_name, fm_field, fm_value):
        try:
            return int(fm_value)
        except ValueError:
            return fm_value

    @staticmethod
    def _try_positive_int(model_name, fm_field, fm_value):
        attempts = [
            lambda x: abs(int(x)),
            lambda x: abs(int(_strip_non_numbers(x)))
        ]
        for func in attempts:
            try:
                return func(fm_value)
            except ValueError:
                pass
        return fm_value

    @staticmethod
    def _handle_record_status(model_name, fm_field, fm_value):
        fm_value = fm_value.title()
        if not fm_value:
            return True, u'Active', u'Set active by default'
        match = re.match('(In)?[aA]ctive(.*)', fm_value)
        if match:
            public_raw, explanation_raw = match.groups()
            public = False if public_raw else True
            explanation = explanation_raw.strip()
            status = 'Active' if public else 'Inactive'
        else:
            match = re.match('Redirect(.*)', fm_value)
            if match:
                explanation_raw = match.groups()[0].strip()
                public, status, explanation = False, u'Redirect', explanation_raw
            else:
                public, status, explanation = True, u'Active', u''
        return public, status, explanation

    @staticmethod
    def _handle_attribute_value(model_name, fm_field, fm_value):
        if fm_field == 'DateBegin':
            return (fm_value, 'BGN')
        elif fm_field == 'DateEnd':
            return (fm_value, 'END')

    @staticmethod
    def _handle_language(model_name, fm_field, fm_value):
        return languageLookup.get(fm_value.lower(), None)

    @staticmethod
    def _handle_citation_fk(model_name, fm_field, fm_value):
        if fm_value == 'CBB0':
            return None
        return fm_value

    fields = {
        'StaffNotes': 'administrator_notes',
        'RecordStatus': ('public',
                         'record_status_value',
                         'record_status_explanation'),
        'RecordHistory': 'record_history',
        'ID': 'id',
        'Dataset': 'dataset',
        'CreatedBy': 'created_by_fm',
        'CreatedOn': 'created_on_fm',
        'ModifiedBy': 'modified_by_fm',
        'ModifiedOn': 'modified_on_fm',
        'Description': 'description',
        'Name': 'name',
        'Type.free': 'type_free',
        'Type.controlled': 'type_controlled',
        'DataDisplayOrder': 'data_display_order',
        'ConfidenceMeasure': 'confidence_measure',
        'RelationshipWeight': 'relationship_weight',

        'citation': {
            'Abstract': 'abstract',
            'Title': 'title',
            'Type.controlled': 'type_controlled',
            'AdditionalTitles': 'additional_titles',
            'BookSeries': 'book_series',
            'EditionDetails': 'edition_details',
            'PhysicalDetails': 'physical_details',
            'RecordHistory': 'record_history',
            'NotesOnContent.notpublished': 'administrator_notes',
            'NotesOnProvenance': 'record_history',
            'Language': 'language',
        },
        'partdetails': {
            'IssueBegin': 'issue_begin',
            'IssueEnd': 'issue_end',
            'IssueFreeText': 'issue_free_text',
            'PageBegin': 'page_begin',
            'PageEnd': 'page_end',
            'PagesFreeText': 'pages_free_text',
            'VolumeEnd': 'volume_end',
            'VolumeBegin': 'volume_begin',
            'VolumeFreeText': 'volume_free_text',
            'Extent': 'extent',
            'ExtentNote': 'extent_note',
            'ID': None,           # These are all fields from Citation that we
            'CreatedBy': None,    #  don't want in PartDetails.
            'CreatedOn': None,
            'ModifiedBy': None,
            'ModifiedOn': None,
            'Description': None,
            'Dataset':  None,
            'RecordStatus': None,
            'Type.controlled': None,
            'RecordHistory': None,
            'StaffNotes': None,
        },
        'authority': {
            'ClassificationSystem': 'classification_system',
            'ClassificationCode': 'classification_code',
            'ClassificationHierarchy': 'classification_hierarchy',
            'RedirectTo': 'redirect_to',
        },
        'person': {
            'PersonalNameFirst': 'personal_name_first',
            'PersonalNameLast': 'personal_name_last',
            'PersonalNameSuffix': 'personal_name_suffix',
            'PersonalNamePreferredForm': 'personal_name_preferred'
        },
        'acrelation': {
            'ID.Authority.link': 'authority',
            'ID.Citation.link': 'citation',
            'Type.Broad.controlled': 'type_broad_controlled',
            'PersonalNameFirst': 'personal_name_first',
            'PersonalNameLast': 'personal_name_last',
            'PersonalNameSuffix': 'personal_name_suffix',
        },
        'ccrelation': {
            'ID.Subject.link': 'subject',
            'ID.Object.link': 'object',
        },
        'tracking': {
            'ID.Subject.link': 'subject',
            'TrackingInfo': 'tracking_info',
            'Notes': 'notes',
        },
        'attribute': {
            'ID.Subject.link': 'source',
            'DateAttribute.free': 'value_freeform',
            'DateBegin': ('value', 'type_qualifier'),
            'DateEnd': ('value', 'type_qualifier'),
            'Type.Broad.controlled': 'type_controlled_broad',
            'Type.controlled': 'type_controlled',
        },
        'linkeddata': {
            'AccessStatus': 'access_status',
            'AccessStatusDateVerified': 'access_status_date_verified',
            'ID.Subject.link': 'subject',
            'Type.controlled': 'type_controlled',
            'Type.Broad.controlled': 'type_controlled_broad',
            'UniversalResourceName.link': 'universal_resource_name',
            'NameOfResource': 'resource_name',
            'URLOfResource': 'url',
        }
    }

    mappings = {
        'classification_system': {
            'WELDON THESAURUS TERMS (2002-PRESENT)': 'SPWT',
            'WELDON THESAURUS': 'SPWT',
            'WELDON CLASSIFICATION SYSTEM (2002-PRESENT)': 'SPWC',
            'SWP': 'SPWC',
            'NEU': 'NEU',
            'MW': 'MW',
            'SHOT': 'SHOT',
            'SHOT THESAURUS TERMS': 'SHOT',
            'GUERLAC COMMITTEE CLASSIFICATION SYSTEM (1953-2001)': 'GUE',
            'WHITROW CLASSIFICATION SYSTEM (1913-1999)': 'MW',
            'FORUM FOR THE HISTORY OF SCIENCE IN AMERICA': 'FHSA',
            'SEARCH APP CONCEPT': 'SAC',
            'PROPER NAME': 'PN',
        },
        'type_broad_controlled': {
            'acrelation': {
                'HASPERSONALRESPONSIBILITYFOR': 'PR',
                'PROVIDESSUBJECTCONTENTABOUT': 'SC',
                'ISINSTITUTIONALHOSTOF': 'IH',
                'ISPUBLICATIONHOSTOF': 'PH',
            }
        },
        'created_on_fm': _as_datetime,
        'modified_on_fm': _as_datetime,
        'extent': _try_positive_int,
        'issue_begin': _try_int,
        'issue_end': _try_int,
        'page_begin': _try_int,
        'page_end': _try_int,
        'volume_begin': _try_int,
        'volume_end': _try_int,
        'data_display_order': _to_float,
        'access_status_date_verified': _as_datetime,
        ('public',
         'record_status_value',
         'record_status_explanation'): _handle_record_status,
        ('value', 'type_qualifier'): {
            'attribute': _handle_attribute_value,
        },
        'language': _handle_language,
        'subject': {
            'ccrelation': _handle_citation_fk,
        },
        'type_controlled': {
            'citation': {
                'BOOK': 'BO',
                'ARTICLE': 'AR',
                'CHAPTER': 'CH',
                'REVIEW': 'RE',
                'ESSAYREVIEW': 'ES',
                'ESSAY REVIEW': 'ES',
                'THESIS': 'TH',
                'EVENT': 'EV',
                'PRESENTATION': 'PR',
                'INTERACTIVERESOURCE': 'IN',
                'INTERACTIVE RESOURCE': 'IN',
                'WEBSITE': 'WE',
                'APPLICATION': 'AP',
            },
            'authority': {
                'PERSON': 'PE',
                'PUBLISHER': 'PU',
                'INSTITUTION': 'IN',
                'TIMEPERIOD': 'TI',
                'GEOGRAPHICTERM': 'GE',
                'SERIALPUBLICATION': 'SE',
                'CLASSIFICATIONTERM': 'CT',
                'CONCEPT': 'CO',
                'CREATIVEWORK': 'CW',
                'EVENT': 'EV',
                'PUBLISHERS': 'PU',
                'CROSS-REFERENCE': 'CR',
            },
            'person': {
                'PERSON': 'PE',
                'INSTITUTION': 'IN',
                'TIMEPERIOD': 'TI',
                'GEOGRAPHICTERM': 'GE',
                'SERIALPUBLICATION': 'SE',
                'CLASSIFICATIONTERM': 'CT',
                'CONCEPT': 'CO',
                'CREATIVEWORK': 'CW',
                'EVENT': 'EV',
                'PUBLISHERS': 'PU',
                'PUBLISHER': 'PU',
                'CROSS-REFERENCE': 'CR',
            },
            'acrelation': {
                'AUTHOR': 'AU',
                'EDITOR': 'ED',
                'ADVISOR': 'AD',
                'CONTRIBUTOR': 'CO',
                'TRANSLATOR': 'TR',
                'SUBJECT': 'SU',
                'CATEGORY': 'CA',
                'PUBLISHER': 'PU',
                'SCHOOL': 'SC',
                'INSTITUTION': 'IN',
                'MEETING': 'ME',
                'PERIODICAL': 'PE',
                'BOOKSERIES': 'BS',
                'COMMITTEE MEMBER': 'CM',
            },
            'ccrelation': {
                'INCLUDESCHAPTER': 'IC',
                'INCLUDESSERIESARTICLE': 'ISA',
                'ISREVIEWOF': 'RO',
                'ISREVIEWEDBY': 'RB',
                'RESPONDSTO': 'RE',
                'ISASSOCIATEDWITH': 'AS'
            },
            'tracking': {
                'HSTMUPLOAD': 'HS',
                'PRINTED': 'PT',
                'AUTHORIZED': 'AU',
                'PROOFED': 'PD',
                'FULLYENTERED': 'FU',
                'BULK DATA UPDATE': 'BD'
            }
        }
    }

    def __init__(self, handler):
        """

        Parameters
        ----------
        handler : object
        """
        self.handler = handler

    def _map_field_value(self, model_name, fm_field, fm_value):
        """
        Given a model and a filemaker field/value pair, obtain the correct
        model field and value.

        The configuration in FMPDSOParser.mappings is used to convert
        ``fm_value`` to the correct Python type for the identified model field.

        Parameters
        ----------
        model_name : str
            Must be the (lowercase normed) name of a model in
            :mod:`isiscb.isisdata.models`\.
        fm_field : str
            Name of a field in the FileMaker database.
        fm_value : str
            Raw value from the FileMaker database.

        Returns
        -------
        model_field : str
        value
            The type of this object will depend on the model field.
        """
        if not fm_value:
            return []

        fm_field = fm_field.replace('Modiefied', 'Modified')
        model_field = self.fields[model_name].get(fm_field, False)
        if model_field is None:
            return []

        if not model_field:
            model_field = self.fields.get(fm_field, False)
            if not model_field:
                return []    # Skip the field.

        # ``mapper`` is a function (staticmethod) or dict. See
        #   :prop:`FMPDSOParser.mappings`.
        mapper = self.mappings.get(model_field, None)

        # This might not be necessary, but I'm paranoid.
        value = copy.copy(fm_value).strip()

        if mapper:
            attrs = (model_name, fm_field, value.upper())

            # If the mapper is a method of some kind, it applies to all models
            #  with this field.
            if type(mapper) is staticmethod:
                value = self.mappings[model_field].__func__(*attrs)

            # Otherwise, it may be model-specific or not. If it's
            #  model-specific, then we should find an entry for the model name
            #  in the mapper.
            elif hasattr(mapper, 'get'):
                # If there is a model-specific mapping, then we prefer that
                #  over a more general mapping.
                model_mapper = mapper.get(model_name, mapper)

                # The mapper itself may be a static method...
                if type(model_mapper) is staticmethod:
                    value = model_mapper.__func__(*attrs)
                # ...or a hashmap (dict).
                elif hasattr(model_mapper, 'get'):
                    value = model_mapper.get(value.upper(), value)

            # This should only be falsey if it is set explicitly.
            if not value:
                return []


        # A single field/value in FM may map to two or more fields/values in
        #  IsisCB Explore.
        if type(model_field) is tuple and type(value) is tuple:
            return list(zip(model_field, value))
        return [(model_field, value)]

    def _get_handler(self, model_name):
        """
        The class of the handler instance (passed to constructor, and assigned
        to ``self.handler``) should define a handler method for each model,
        named ``handle_[model_name]``.

        Parameters
        ----------
        model_name : str
            Must be the (lowercase normed) name of a model in
            :mod:`isiscb.isisdata.models`\.

        Returns
        -------
        instancemethod
        """
        return getattr(self.handler, 'handle_%s' % model_name, None)

    def _tag(self, element):
        return copy.copy(element.tag).replace(self.fm_namespace, '')

    def parse_record(self, record, model_name, parse_also=None):
        """
        Parse a single row of data from FMPDSO XML.
        """
        # There are some strange elements early in the XML document that we
        #  don't care about. <ROW>s hold the data that we're after.
        if self._tag(record) != 'ROW':
            return

        fielddata = []
        extra = [[] for _ in parse_also]
        for element in record.getchildren():
            fm_field = self._tag(element)
            fm_value = copy.copy(element.text)
            fielddata += self._map_field_value(model_name, fm_field, fm_value)

            # Data for some models (e.g. Citation, Authority) need to be
            #  handled at the same time as data for other models (e.g.
            #  PartDetails, Person).
            if parse_also:
                for i, extra_model in enumerate(parse_also):
                    args = (extra_model, fm_field, fm_value)
                    extra[i] += self._map_field_value(*args)

        # The class of the handler instance (passed to constructor, and set to
        #  self.handler) should define a handler method for each model.
        handler = self._get_handler(model_name)
        if not handler:
            return
        return handler(fielddata, extra)

    def parse(self, model_name, data_path, parse_also):
        """
        Kick off parsing for a single FMPDSO XML document.

        Parameters
        ----------
        model_name : str
            Must be the (lowercase-normed) name of a
            :class:`django.db.models.Model` subclass in
            :mod:`isiscb.isisdata.models`\.
        data_path : str
            Location of the XML document.
        parse_also : list
            Names of other models that should be parsed at the same time.
        """

        # This is a much more memory-friendly approach -- ET does all kinds of
        #  crazy copying otherwise. The trade-off is that we only get one crack
        #  each element that streams through.
        fast_iter(ET.iterparse(data_path),     # Iterator.
                  self.parse_record,           # Method.
                  'ROW',
                  model_name,                  # Extra...
                  parse_also)


class VerboseHandler(object):
    """
    Just for testing.
    """
    def handle_citation(self, fielddata, extra):
        pprint.pprint(fielddata)

    def handle_authority(self, fielddata, extra):
        pprint.pprint(fielddata)


class DatabaseHandler(object):
    """
    Updates the IsisCB Explore database using data yielded by the
    :class:`.FMPDSOParser`\.
    """

    pk_fields = ['language', 'subject', 'object', 'citation', 'authority',
                 'redirect_to', 'source']
    """
    When these fields are encountered, `_id` will be appended to the field
    name.
    """

    id_prefixes = {
        'CBB': 'citation',
        'CBA': 'authority',
        'ACR': 'acrelation',
        'AAR': 'aarelation',
        'CCR': 'ccrelation',
    }
    """
    Maps ID prefixes onto model names.
    """

    def __init__(self, print_every=200):
        self.model_counts = Counter()
        self.print_every = print_every
        self.errors = []
        try:
            with open('/home/ec2-user/ingest_errors.pickle', 'r') as f:
                self.errors += pickle.load(f)
        except:
            pass

    def _tick(self, model_name):
        self.model_counts[model_name] += 1
        N = self.model_counts[model_name]
        if N % self.print_every == 0:
            pprint.pprint("handled %i %s records" % (N, model_name))

    def _get_subject(self, subject_id):
        """
        Obtain the ID of the ContentType instance corresponding to the object
        with ID ``subject_id``.

        Parameters
        ----------
        subject_id : str

        Returns
        -------
        int
            Primary key ID for the ContentType instance for the object's
            model class.
        """
        model_name = self.id_prefixes[subject_id[:3]]
        return ContentType.objects.get(model=model_name).id

    def _update_with(self, instance, data):
        """
        Update a db model ``instance`` with values in ``data``.

        Parameters
        ----------
        instance : :class:`django.db.models.Model`
        data : dict
        """
        for field, value in list(data.items()):
            setattr(instance, field, value)
        instance.save()

    def _prepare_data(self, model, data):
        """
        Converts ``data`` to a dict, and makes any necessary modifications to
        field names.

        Parameters
        ----------
        data : list
            A list of (fieldname, value) tuples.

        Returns
        -------
        dict
        """

        prepped_data = {}
        for field, value in list(dict(data).items()):
            if field in self.pk_fields:
                field += '_id'
            prepped_data[field] = value
        return prepped_data

    def _fix_partdetails(self, partdetails_data):
        """
        Occassionally non-int data will be entered in int-only fields for
        :class:`.PartDetails`\. If so, we pass the value off to the
        corresponding ``free_text`` field, and remove the non-conforming field.
        """
        int_fields = [
            'issue_end', 'issue_begin',
            'page_begin', 'page_end',
            'volume_begin', 'volume_end'
        ]
        partdetails_data_fixed = {}
        for key, value in list(partdetails_data.items()):
            if key in int_fields and type(value) is not int:
                prefix = key.split('_')[0]
                freetext_key = prefix + u'_free_text'
                # Don't overwrite existing data.
                if freetext_key in partdetails_data:
                    continue
                key = freetext_key
            partdetails_data_fixed[key] = value
        return partdetails_data_fixed

    def _handle_dataset(self, literal):
        if type(literal) in [str, str]:
            match = re.search('([^(]+)[(](.+)[)]', literal)
            if match:
                datasetname, editorname  = match.groups()
                dataset, _ = Dataset.objects.get_or_create(name=datasetname)
                subdataset, _ = Dataset.objects.get_or_create(name=literal,
                                                              defaults={'belongs_to': dataset})
                return 'belongs_to', subdataset
            else:
                dataset, _ = Dataset.objects.get_or_create(name=literal)
                return 'belongs_to', dataset
        return 'dataset_literal', literal


    def handle_citation(self, fielddata, extra):
        """
        Create or update a :class:`.Citation` with ``fielddata``.

        Parameters
        ----------
        fielddata : list
            A list of (fieldname, value) tuples.
        extra : list
            Items are lists in the same format as ``fielddata``.
        """

        citation_data = self._prepare_data(Citation, fielddata)
        citation_id = citation_data.pop('id')    # Don't want this in update.
        language_id = citation_data.pop('language_id', None)

        dataset = citation_data.pop('dataset', None)
        if dataset:
            key, value = self._handle_dataset(dataset)
            citation_data['dataset_literal'] = dataset
            citation_data[key] = value

        try:
            citation, created = Citation.objects.update_or_create(
                pk=citation_id,
                defaults=citation_data
            )
        except Exception as E:
            print(citation_data, citation_id)
            raise E

        if language_id:
            citation.language.add(language_id)

        partdetails_data = self._prepare_data(PartDetails, extra[0])
        partdetails_data = self._fix_partdetails(partdetails_data)

        if not created:
            if citation.part_details and len(partdetails_data) > 0:
                self._update_with(citation.part_details, partdetails_data)

        if (created or not citation.part_details) and len(partdetails_data) > 0:
            try:
                part_details = PartDetails.objects.create(**partdetails_data)
            except Exception as E:
                print(partdetails_data)
                raise E

            citation.part_details = part_details
            citation.save()

        self._tick('citation')

    def handle_authority(self, fielddata, extra):
        """
        Create or update an :class:`.Authority` with ``fielddata``.

        Parameters
        ----------
        fielddata : list
            A list of (fieldname, value) tuples.
        extra : list
            Items are lists in the same format as ``fielddata``.
        """

        authority_data = self._prepare_data(Authority, fielddata)
        person_data = self._prepare_data(Person, extra[0])

        if authority_data['record_status_value'] == CuratedMixin.ACTIVE:
            authority_data['public'] = True

        if person_data and authority_data.get('type_controlled') == 'PE':
            model = Person
            authority_data.update(person_data)
        else:
            model = Authority

        try:
            authority, created = model.objects.update_or_create(
                pk=authority_data['id'],
                defaults=authority_data
            )

        except Exception as E:
            # If this record redirects to a record that has not yet been
            #  created, update_or_create() will throw an IntegrityError.
            if type(E) is IntegrityError and authority_data.get('record_status_value').lower() == 'redirect':
                redirect_to = authority_data.get('redirect_to_id')
                Authority.objects.create(**{
                    'pk': redirect_to,
                    'type_controlled': authority_data.get('type_controlled'),
                    'public': True,
                    'record_status_value': 'Active',
                })
                try:
                    authority, created = model.objects.update_or_create(
                        pk=authority_data['id'],
                        defaults=authority_data
                    )
                except Exception as E:
                    self.errors.append(('authority', E.__repr__(), authority_data['id'], authority_data))
                    print(authority_data)
                    raise E
        self._tick('authority')

    def handle_ccrelation(self, fielddata, extra):
        """
        Create or update a :class:`.CCRelation` with ``fielddata``.

        Parameters
        ----------
        fielddata : list
            A list of (fieldname, value) tuples.
        extra : list
            Items are lists in the same format as ``fielddata``.
        """
        ccrelation_data = self._prepare_data(CCRelation, fielddata)
        ccrelation_id = ccrelation_data.pop('id')

        try:
            ccrelation, created = CCRelation.objects.update_or_create(
                pk=ccrelation_id,
                defaults=ccrelation_data
            )
        except Exception as E:
            self.errors.append(('ccrelation', E.__repr__(), ccrelation_id, ccrelation_data))
        self._tick('ccrelation')

    def handle_acrelation(self, fielddata, extra):
        """
        Create or update a :class:`.ACRelation` with ``fielddata``.

        Parameters
        ----------
        fielddata : list
            A list of (fieldname, value) tuples.
        extra : list
            Items are lists in the same format as ``fielddata``.
        """

        acrelation_data = self._prepare_data(ACRelation, fielddata)
        acrelation_id = acrelation_data.pop('id')
        try:
            acrelation, created = ACRelation.objects.update_or_create(
                pk=acrelation_id,
                defaults=acrelation_data
            )
        except Exception as E:
            print(E.__repr__(), acrelation_id, acrelation_data)
            self.errors.append(('acrelation', E.__repr__(), acrelation_id, acrelation_data))
        self._tick('acrelation')

    def handle_attribute(self, fielddata, extra):
        """
        Create or update an :class:`.Attribute` with ``fielddata``.

        Parameters
        ----------
        fielddata : list
            A list of (fieldname, value) tuples.
        extra : list
            Items are lists in the same format as ``fielddata``.
        """

        N_values = 0
        datasets = []
        value_data = []
        for field, value in fielddata:
            if field == 'value':
                value_data.append(value)
        N_values = len(value_data)
        if len(value_data) == 1:
            value_data = value_data[0]

        # If the row has some problem, there may not be an actual Value.
        if not value_data:
            return

        attribute_data = self._prepare_data(Attribute, fielddata)
        attribute_id = attribute_data.pop('id', None)

        # `subject` is a generic relation; an Attribute can describe anything.
        subject_id = attribute_data.pop('source_id')
        subject_type_id = self._get_subject(subject_id)
        attribute_data.update({
            'source_content_type_id': subject_type_id,
            'source_instance_id': subject_id,
        })

        # We don't want these in the data for Attribute.
        attribute_data.pop('type_qualifier', None)
        attribute_data.pop('value', None)
        try:
            type_controlled = attribute_data.pop('type_controlled')
        except KeyError as E:
            print(E.__repr__(), attribute_id, attribute_data)
            self.errors.append(('attribute', E.__repr__(), attribute_id, attribute_data))
            return


        if type_controlled == 'BirthToDeathDates' or \
            (type(value_data) in [list, tuple] and len(value_data) == 2):
            value_model = ISODateRangeValue
        elif 'date' in type_controlled.lower():
            value_model = ISODateValue
        else:
            value_model = dict(VALUE_MODELS)[type(value_data)]

        try:
            value_model_ctype = ContentType.objects.get_for_model(value_model)
            attribute_type, _ = AttributeType.objects.update_or_create(
                name=type_controlled,
                defaults={
                    'value_content_type_id': value_model_ctype.id
                }
            )
        except Exception as E:
            print(E.__repr__(), attribute_id, attribute_data)
            self.errors.append(('attribute', E.__repr__(), attribute_id, attribute_data))

        attribute_data.update({
            'type_controlled_id': attribute_type.id,
        })
        try:
            attribute, created = Attribute.objects.update_or_create(
                pk=attribute_id,
                defaults=attribute_data
            )
        except Exception as E:
            print(E.__repr__(), attribute_id, attribute_data)
            self.errors.append(('attribute', E.__repr__(), attribute_id, attribute_data))

        # try:
        if not hasattr(attribute, 'value'):
            try:
                value = value_model.objects.create(
                    value=value_data,
                    attribute=attribute
                )
            except Exception as E:
                print(E.__repr__(), attribute_id, attribute_data)
                self.errors.append(('value', E.__repr__(), attribute_id, value_data))
        else:
            child_class = attribute.value.get_child_class()
            if type(child_class) != value_model:
                attribute.value.delete()
                try:
                    value = value_model.objects.create(
                        value=value_data,
                        attribute=attribute
                    )
                except Exception as E:
                    print(E.__repr__(), attribute_id, attribute_data)
                    self.errors.append(('value', E.__repr__(), attribute_id, value_data))
            else:
                try:
                    self._update_with(attribute.value, {'value': value_data})
                except Exception as E:
                    print(E.__repr__(), attribute_id, attribute_data)
                    self.errors.append(('value', E.__repr__(), attribute_id, value_data))
                value = attribute.value
        # except Exception as E:
        #     print E.__repr__(), attribute_id, attribute_data
        #     self.errors.append(('value', E.__repr__(), attribute_id, value_data))

        if 'value_freeform' not in attribute_data or not attribute.value_freeform:
            attribute.value_freeform = attribute.value.__unicode__()
            attribute.save()

        self._tick('attribute')

    def handle_linkeddata(self, fielddata, extra):
        """
        Create or update a :class:`.LinkedData` with ``fielddata``.

        Parameters
        ----------
        fielddata : list
            A list of (fieldname, value) tuples.
        extra : list
            Items are lists in the same format as ``fielddata``.
        """
        linkeddata_data = self._prepare_data(LinkedData, fielddata)
        linkeddata_id = linkeddata_data.pop('id')

        # `subject` is a generic relation; an Attribute can describe anything.
        subject_id = linkeddata_data.pop('subject_id')
        subject_type_id = self._get_subject(subject_id)

        # Get the LinkedDataType instance for this LinkedData.
        type_controlled = linkeddata_data.pop('type_controlled')
        ld_type, _ = LinkedDataType.objects.get_or_create(name=type_controlled)

        linkeddata_data.update({
            'subject_content_type_id': subject_type_id,
            'subject_instance_id': subject_id,
            'type_controlled_id': ld_type.id,
        })

        try:
            linkeddata, created = LinkedData.objects.update_or_create(
                pk=linkeddata_id,
                defaults=linkeddata_data
            )
        except Exception as E:
            self.errors.append(('linkeddata', E.__repr__(), linkeddata_id, linkeddata_data))
        self._tick('linkeddata')

    def handle_tracking(self, fielddata, extra):
        """
        Create or update a :class:`.Tracking` with ``fielddata``.

        Parameters
        ----------
        fielddata : list
            A list of (fieldname, value) tuples.
        extra : list
            Items are lists in the same format as ``fielddata``.
        """
        tracking_data = self._prepare_data(Tracking, fielddata)
        tracking_id = tracking_data.pop('id')

        subject_id = tracking_data.pop('subject_id')
        subject_type_id = self._get_subject(subject_id)
        tracking_data.update({
            'subject_content_type_id': subject_type_id,
            'subject_instance_id': subject_id,
        })

        try:
            tracking, created = Tracking.objects.update_or_create(
                pk=tracking_id,
                defaults=tracking_data
            )
        except Exception as E:
            self.errors.append(('tracking', E.__repr__(), tracking_id, tracking_data))
        self._tick('tracking')

    def __del__(self):
        import pickle as pickle
        try:
            with open('/home/ec2-user/ingest_errors.pickle', 'w') as f:
                pickle.dump(self.errors, f)
        except:
            pass

class Command(BaseCommand):
    help = 'Update the IsisCB Explore database with FileMaker Pro FMPDSO XML.'

    def __init__(self, *args, **kwargs):
        self.failed = []
        return super(Command, self).__init__(*args, **kwargs)

    def _get_subject(self, subject_id):
        model_name = model_ids[subject_id[:3]]
        subject_ctype = ContentType.objects.get(model=model_name).id
        return subject_ctype

    def add_arguments(self, parser):
        parser.add_argument('datapath', nargs=1, type=str)
        parser.add_argument('table', nargs='*', type=str)

    def handle(self, *args, **options):
        parser = FMPDSOParser(DatabaseHandler())
        table = options['table'][0]

        if table == 'citation':
            parse_also = ['partdetails']
        elif table == 'authority':
            parse_also = ['person']
        else:
            parse_also = []

        dirpath = os.path.join(options['datapath'][0], table)
        if os.path.exists(dirpath) and os.path.isdir(dirpath):
            for fname in os.listdir(dirpath):
                if fname.startswith(table) and fname.endswith('xml'):
                    path = os.path.join(dirpath, fname)
                    print('processing %s' % fname)
                    parser.parse(table, path, parse_also)
        else:
            path = os.path.join(options['datapath'][0], '%s.xml' % table)
            parser.parse(table, path, parse_also)
