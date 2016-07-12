from unittest import TestCase
from django.test.client import RequestFactory
from django.contrib.contenttypes.models import ContentType
from django.db import models

import rdflib
import datetime

from parser import *
from models import *
from suggest import *
from tasks import *


# Create your tests here.
datapath = 'zotero/test_data/IsisCBTest.rdf'

AUTHOR = rdflib.URIRef("http://purl.org/net/biblio#authors")

partdetails_fields = [
    ('page_start', 'page_begin'),
    ('page_end', 'page_end'),
    ('pages_free_text', 'pages_free_text'),
    ('issue', 'issue_free_text'),
    ('volume', 'volume_free_text'),
]


class TestSubjects(TestCase):
    def test_parse_subjects(self):
        papers = read('zotero/test_data/Hist Europ Idea 2015 41 7.rdf')
        for paper in papers:
            self.assertIn('subjects', paper.__dict__)

    def test_process_subjects(self):
        Authority.objects.create(name='testauthority', classification_code='140-340')

        papers = read('zotero/test_data/Hist Europ Idea 2015 41 7.rdf')
        instance = ImportAccession.objects.create(name='TestAccession')
        citations = process(papers, instance)
        for citation in citations:
            for acrelation in citation.authority_relations.filter(type_controlled=DraftACRelation.SUBJECT):
                if acrelation.authority.name == 'testauthority':
                    self.assertEqual(acrelation.authority.resolutions.count(), 1)



class TestParse(TestCase):
    def test_parse(self):
        """
        There should not be a Paper for every relevant entry in the RDF.
        """
        papers = read(datapath)

        graph = rdflib.Graph()
        graph.parse(datapath)
        expected = 0
        for element in ZoteroParser.entry_elements:
            query = 'SELECT * WHERE { ?p a %s }' % element
            expected += len([r[0] for r in graph.query(query)])

        self.assertNotEqual(len(papers), expected)

    def test_parse_authors(self):
        """
        There should be a unique author for each unique author in the RDF.
        """
        papers = read(datapath)


        parsed_authors = set([])    # Unique authors.
        parsed_authorships = 0      # Paper-Author associations.
        for paper in papers:
            parsed_authorships += len(paper.authors_full)
            for author in paper.authors_full:
                parsed_authors.add(author)

        graph = rdflib.Graph()
        graph.parse(datapath)
        expected_authors = set([])    # Unique authors.
        expected_authorships = 0      # Paper-Author associations.
        for s, p, o in graph.triples((None, AUTHOR, None)):
            expected_authors.add(o)
            expected_authorships += 1

        self.assertEqual(len(parsed_authors), len(expected_authors))
        self.assertEqual(parsed_authorships, expected_authorships)

    def test_parse_titles(self):
        """
        Each entry should have a title.
        """
        papers = read(datapath)
        for paper in papers:
            self.assertGreater(len(paper.title), 0)

    def test_parse_dates(self):
        """
        Each entry should have a date.
        """
        papers = read(datapath)
        for paper in papers:
            self.assertTrue(hasattr(paper, 'date'))

    def test_parse_types(self):
        papers = read(datapath)
        for paper in papers:
            self.assertTrue(hasattr(paper, 'documentType'))
            self.assertEqual(len(paper.documentType), 2)
            self.assertIn(paper.documentType, ZoteroParser.document_types.values())


class TestIngest(TestCase):
    def setUp(self):
        self.instance = ImportAccession.objects.create(name='TestAccession')

    def test_process_paper(self):
        papers = read(datapath)
        for paper in papers:
            draftCitation = process_paper(paper, self.instance)
            self.assertIsInstance(draftCitation, DraftCitation)

    def test_handle_authorities(self):
        papers = read(datapath)

        for paper in papers:
            authorities, acrelations = process_authorities(paper, self.instance)
            self.assertGreater(len(authorities), 0)
            self.assertGreater(len(acrelations), 0)

    def test_handle_linkeddata(self):
        papers = read(datapath)
        for paper in papers:
            ldentries = process_linkeddata(paper, self.instance)

    def test_process(self):
        papers = read(datapath)
        citations = process(papers, self.instance)

        self.assertGreater(len(citations), 0)
        self.assertIsInstance(citations[0], DraftCitation)


class TestSuggest(TestCase):
    def test_suggest_citation_by_linkeddata(self):
        accession = ImportAccession(name='test')
        accession.save()
        papers = read(datapath)
        citations = process(papers, accession)


class TestIngest(TestCase):
    """
    After all :class:`.DraftAuthority` instances have been resolved for a
    :class:`.ImportAccession`\, the curator will elect to ingest all of the
    records in that accession into the production database.
    """

    def setUp(self):
        self.dataset = Dataset.objects.create(name='test dataset')
        self.accession = ImportAccession.objects.create(name='test',
                                                        ingest_to=self.dataset)
        self.papers = read(datapath)
        self.citations = process(self.papers, self.accession)

        # We need a user for the accession.
        rf = RequestFactory()
        self.request = rf.get('/hello/')
        self.user = User.objects.create(username='bob', password='what', email='asdf@asdf.com')
        self.request.user = self.user

        isodate_type = ContentType.objects.get_for_model(ISODateValue)
        self.publicationDateType, _ = AttributeType.objects.get_or_create(
            name='PublicationDate',
            value_content_type=isodate_type,
            display_name='Publication date',
        )

        # The ImportAccession should be fully resolved, so we need to create
        #  corresponding Authority records ahead of time.
        for draftauthority in self.accession.draftauthority_set.all():
            authority = Authority.objects.create(
                name = draftauthority.name,
                type_controlled = draftauthority.type_controlled,
            )
            InstanceResolutionEvent.objects.create(
                for_instance = draftauthority,
                to_instance = authority,
            )
        self.accession.draftauthority_set.all().update(processed=True)

    def test_ingest_accession(self):
        citation = ingest_accession(self.request, self.accession)
        self.accession.refresh_from_db()

        self.assertEqual(self.accession.citation_set.count(),
                         self.accession.draftcitation_set.count(),
                         'did not ingest all citations')

    def test_ingest_citation(self):
        draftcitation = self.citations[1]
        citation = ingest_citation(self.request, self.accession, draftcitation)

        self.assertIsInstance(citation.created_on, datetime.datetime,
                              'created_on not populated correctly')
        self.assertIsInstance(citation.created_by, User,
                              'created_by not populated correctly')
        self.assertIsInstance(citation.publication_date, datetime.date,
                              'publication_date not populated correctly')
        self.assertFalse(citation.public,
                         'new citation is public; should be non-public')
        self.assertEqual(citation.record_status_value, CuratedMixin.INACTIVE,
                         'new citation is not inactive')
        self.assertEqual(citation.title, draftcitation.title,
                         'title not transferred correctly')
        self.assertEqual(citation.type_controlled,
                         draftcitation.type_controlled,
                         'type_controlled not transferred correctly')
        self.assertTrue(draftcitation.processed,
                        'DraftCitation not flagged as processed')

        self.assertEqual(self.accession.ingest_to, citation.belongs_to,
                         'citation not assigned to the correct dataset')


        model_fields = {f.name: type(f) for f in PartDetails._meta.fields}
        for field, pfield in partdetails_fields:
            draft_value = getattr(draftcitation, field, None)
            if model_fields[pfield] is models.IntegerField:
                try:
                    draft_value = int(draft_value)
                except ValueError:
                    continue

            prod_value = getattr(citation.part_details, pfield, None)
            self.assertEqual(draft_value, prod_value,
                             '%s not populated correctly, %s != %s' % \
                             (pfield, draft_value, prod_value))

        for draft in draftcitation.authority_relations.all():
            self.assertTrue(draft.processed,
                            'DraftACRelation not flagged as processed')
            self.assertEqual(draft.resolutions.count(), 1,
                             'resolution not created for DraftACRelation')

            prod = draft.resolutions.first().to_instance
            self.assertEqual(draft.type_controlled, prod.type_controlled,
                             'type_controlled transferred incorrectly')
            self.assertEqual(draft.authority.name,
                             prod.name_for_display_in_citation,
                             'DraftAuthority name not transferred to ACR')

            self.assertEqual(self.accession.ingest_to, prod.belongs_to)

        attribute = citation.attributes.first()
        self.assertEqual(attribute.type_controlled, self.publicationDateType,
                         'attribute has the wrong type')
        self.assertIsInstance(attribute.value.get_child_class(), ISODateValue,
                              'attribute value instantiates the wrong class')

        self.assertEqual(attribute.value.get_child_class().as_date,
                         citation.publication_date,
                         'publication date attribute incorrect')

    def tearDown(self):
        self.accession.delete()
        self.dataset.delete()
        self.user.delete()
