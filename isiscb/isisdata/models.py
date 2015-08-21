from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator

from simple_history.models import HistoricalRecords
import datetime
import pickle
import uuid
import urlparse

class FlexField(models.TextField):
    """
    Accepts any pickle-able Python object, and stores its serialized
    representation as plain text in the database.
    """

    def get_prep_value(self, value, *args, **kwargs):
        """Serialize"""
        if value is None:
            return
        return pickle.dumps(value)

    def from_db_value(self, value, *args, **kwargs):
        """Deserialize"""

        return pickle.loads(value)


class CuratedMixin(models.Model):
    """
    Curated objects have an audit history and curatorial notes attached to them.
    """

    class Meta:
        abstract = True

    administrator_notes = models.TextField(blank=True, help_text="""
    Curatorial discussion about the record.""")

    record_history = models.TextField(blank=True, help_text="""
    Notes about the provenance of the information in this record. e.g. 'supplied
    by the author,' 'imported from SHOT bibliography,' 'generated by crawling UC
    Press website'""")

    modified_on = models.DateTimeField(auto_now=True, null=True, help_text="""
    Date and time at which this object was last updated.""")
    modified_by = models.ForeignKey(User, null=True, blank=True, help_text="""
    The most recent user to modify this object.""")

    @property
    def created_on(self):
        """
        The date and time at which this object was created.

        Retrieves the date of the (one and only) creation HistoricalRecord for
        an instance.
        """
        return self.history.get(history_type='+').history_date

    @property
    def created_by(self):
        """
        The user who created this object.

        Retrieves the user on the (one and only) creation HistoricalRecord for
        an instance.
        """
        return self.history.get(history_type='+').history_user

    # These should be jettisoned after the project moves away from FileMaker.
    created_on_fm = models.DateTimeField(null=True, help_text="""
    Value of CreatedOn from the original FM database.""")

    created_by_fm = models.CharField(max_length=255, blank=True, help_text="""
    Value of CreatedBy from the original FM database.""")

    modified_on_fm = models.DateTimeField(null=True, help_text="""
    Value of ModifiedBy from the original FM database.""")

    modified_by_fm = models.CharField(max_length=255, blank=True, help_text="""
    Value of ModifiedOn from the original FM database.""")

    @property
    def _history_user(self):
        return self.modified_by

    @_history_user.setter
    def _history_user(self, value):
        self.modified_by = value

    @property
    def _history_date(self):
        return self.modified_on

    @_history_date.setter
    def _history_date(self, value):
        self.modified_on = value


class AttributeMixin(models.Model):
    """
    Adds an ``attributes`` field, and methods for accessing related
    :class:`.Attribute`\s.
    """

    class Meta:
        abstract = True

    # Put this here rather than in the Attribute model, since both Citations
    #  and Authorities (and more?) should be able to have attributes.
    attributes = models.ManyToManyField('Attribute', blank=True, null=True)

    def __getattr__(self, name):
        """
        If an instance has no attribute called ``name``, checks the
        ``attributes`` field for matching related :class:`.Attribute`\s.
        """

        # try:    # Give the base class the first shot.
        return super(AttributeMixin, self).__getattr__(name)
        # except AttributeError as E:
            # Look for ``name`` among related Attributes.
        if not self.pk:
            raise E
        queryset = self.attributes.filter(type_controlled=name)
        if queryset.count() == 1:
            return queryset[0].value
        elif querset.count() > 1:
            return [a.value for a in queryset]
            # raise E     # No such attribute found.


class ReferencedEntity(models.Model):
    """
    Provides a custom ID field and an URI field, and associated methods.
    """

    id = models.CharField(max_length=200, primary_key=True, help_text="""
    In the format CBB000000000 (CBB followed by a number padded with zeros to
    be nine digits).""")

    uri = models.URLField(blank=True)

    def generate_uri(self):
        """
        Create a new Unique Resource Identifier.
        """
        return urlparse.urlunparse(('http', settings.DOMAIN, 'entities/{0}'.format(uuid.uuid1()), '', '', ''))

    def save(self, *args, **kwargs):
        """
        If ``uri`` is not set, generate a new one.
        """
        if self.uri == '':
            self.uri = self.generate_uri()
        return super(ReferencedEntity, self).save(*args, **kwargs)


class Language(models.Model):
    """
    Populate this using fixtures/language.json to load ISO 639-1 language codes.
    """

    id = models.CharField(max_length=2, primary_key=True,
                          help_text="""Language code (e.g. ``en``).""")

    name = models.CharField(max_length=255)


class Citation(ReferencedEntity, CuratedMixin, AttributeMixin):
    history = HistoricalRecords()

    title = models.CharField(max_length=255, help_text="""
    The name to be used to identify the resource. For reviews that traditionally
    have no title, this should be added as something like "[Review of Title
    (Year) by Author]".""")

    description = models.TextField(null=True, blank=True, help_text="""
    Used for additional bibliographic description, such as content summary. For
    abstracts use the 'Abstract' field.""")

    BOOK = 'BO'
    ARTICLE = 'AR'
    CHAPTER = 'CH'
    REVIEW = 'RE'
    ESSAY_REVIEW = 'ES'
    THESIS = 'TH'
    EVENT = 'EV'
    PRESENTATION = 'PR'
    INTERACTIVE = 'IN'
    WEBSITE = 'WE'
    APPLICATION = 'AP'

    TYPE_CHOICES = (
        (BOOK, 'Book'),
        (ARTICLE, 'Article'),
        (CHAPTER, 'Chapter'),
        (REVIEW, 'Review'),
        (ESSAY_REVIEW, 'Essay Review'),
        (THESIS, 'Thesis'),
        (EVENT, 'Event'),
        (PRESENTATION, 'Presentation'),
        (INTERACTIVE, 'Interactive Resource'),
        (WEBSITE, 'Website'),
        (APPLICATION, 'Application'),
    )

    type_controlled = models.CharField(max_length=2, choices=TYPE_CHOICES,
                                       help_text="""
    This list can be extended to the resource types specified by Doublin Core
    Recource Types http://dublincore.org/documents/resource-typelist/""")

    abstract = models.TextField(blank=True, help_text="""
    Abstract or detailed summaries of a work.""")

    edition_details = models.TextField(blank=True, help_text="""
    Use for describing the edition or version of the resource. Include names of
    additional contributors if necessary for clarification (such as translators,
    introduction by, etc). Always, use relationship table to list contributors
    (even if they are specified here).""")

    physical_details = models.CharField(max_length=255, blank=True,
                                        help_text="""
    For describing the physical description of the resource. Use whatever
    information is appropriate for the type of resource.""")

    # Storing this in the model would be kind of hacky. This will make it easier
    #  to do things like sort or filter by language.
    language = models.ManyToManyField('Language', help_text="""
    Language of the resource. Multiple languages can be specified.""")

    part_details = models.OneToOneField('PartDetails', null=True, blank=True,
                                        help_text="""
    New field: contains volume, issue, page information for works that are parts
    of larger works.""")

    related_citations = models.ManyToManyField('Citation', through='CCRelation',
                                               related_name='citations_related')
    related_authorities = models.ManyToManyField('Authority',
                                                 through='ACRelation',
                                                 related_name='authorities_related')

    EXTERNAL_PROOF = 'EX'
    QUERY_PROOF = 'QU'
    HOLD = 'HO'
    RLG_CORRECT = 'RC'
    ACTION_CHOICES = (
        (EXTERNAL_PROOF, 'External Proof'),
        (QUERY_PROOF, 'Query Proof'),
        (HOLD, 'Hold'),
        (RLG_CORRECT, 'RLG Correct')
    )

    record_action = models.CharField(max_length=2, blank=True,
                                     choices=ACTION_CHOICES, help_text="""
    Used to track the record through curation process.
    """)

    CONTENT_LIST = 'CL'
    SOURCE_BOOK = 'SB'
    SCOPE = 'SC'
    FIX_RECORD = 'FX'
    DUPLICATE = 'DP'
    STATUS_CHOICES = (
        (CONTENT_LIST, 'Content List'),
        (SOURCE_BOOK, 'Source Book'),
        (SCOPE, 'Scope'),
        (FIX_RECORD, 'Fix Record'),
        (DUPLICATE, 'Duplicate')
    )
    status_of_record = models.CharField(max_length=2, choices=STATUS_CHOICES,
                                        blank=True, help_text="""
    Used to control printing in the paper volume of the CB.
    """)


class Authority(ReferencedEntity, CuratedMixin, AttributeMixin):
    history = HistoricalRecords()

    name = models.CharField(max_length=255, help_text="""
    Name, title, or other main term for the authority as will be displayed.""")

    description = models.TextField(help_text="""
    A brief description that will be displayed to help identify the authority.
    Such as, brief bio or a scope note. For classification terms will be text
    like "Classification term from the XXX classification schema.'""")

    PERSON = 'PE'
    INSTITUTION = 'IN'
    TIME_PERIOD = 'TI'
    GEOGRAPHIC_TERM = 'GE'
    SERIAL_PUBLICATION = 'SE'
    CLASSIFICATION_TERM = 'CT'
    CONCEPT = 'CO'
    CREATIVE_WORK = 'CW'
    EVENT = 'EV'
    TYPE_CHOICES = (
        (PERSON, 'Person'),
        (INSTITUTION, 'Institution'),
        (TIME_PERIOD, 'Time Period'),
        (GEOGRAPHIC_TERM, 'Geographic Term'),
        (SERIAL_PUBLICATION, 'Serial Publication'),
        (CLASSIFICATION_TERM, 'Classification Term'),
        (CONCEPT, 'Concept'),
        (CREATIVE_WORK, 'Creative Work'),
        (EVENT, 'Event')
    )
    type_controlled = models.CharField(max_length=2, choices=TYPE_CHOICES,
                                       help_text="""
    Specifies authority type. Each authority thema has its own list of
    controlled type vocabulary.""")

    # QUESTION: How is this related to "tagging" that users can do?
    SWP = 'SWP'
    NEU = 'NEU'
    MW = 'MW'
    SHOT = 'SHOT'
    CLASS_SYSTEM_CHOICES = (
        (SWP, 'SWP'),
        (NEU, 'Neu'),
        (MW, 'MW'),
        (SHOT, 'SHOT')
    )
    classification_system = models.CharField(max_length=4,
                                             choices=CLASS_SYSTEM_CHOICES,
                                             help_text="""
    Specifies the classification system that is the source of the authority.
    Used to group resources by the Classification system. The system used
    currently is the Weldon System. All the other ones are for reference or
    archival purposes only.""")

    classification_code = models.CharField(max_length=255, help_text="""
    alphanumeric code used in previous classification systems to describe
    classification terms. Primarily of historical interest only. Used primarily
    for Codes for the classificationTerms. however, can be used for other
    kinds of terms as appropriate.""")

    classification_hierarchy = models.CharField(max_length=255, help_text="""
    Used for Classification Terms to describe where they fall in the
    hierarchy.""")

    # what about: redirectTo, dateRange, date.for.sorting?


class Person(Authority):
    history = HistoricalRecords()

    # QUESTION: These seems specific to the PERSON type. Should we be modeling
    #  Authority types separately? E.g. each type could be a child class of
    #  Authority, and we can preserve generic relations to Attributes using
    #  multi-table inheritance. Another reason to do this is that we want
    #  users to be able to "claim" their PERSON record -- this is much more
    #  straightforward with separate models.
    # are those calculated?
    personal_name_last = models.CharField(max_length=255)
    personal_name_first = models.CharField(max_length=255)
    personal_name_suffix = models.CharField(max_length=255)


class ACRelation(ReferencedEntity, CuratedMixin, AttributeMixin):
    history = HistoricalRecords()

    citation = models.ForeignKey('Citation')
    authority = models.ForeignKey('Authority')

    name = models.CharField(max_length=255)
    description = models.TextField()

    # Allowed values depend on the value of the Type.Broad,controlled
    # if Type.Broad.controlled = 'HasPersonalResponsibilityFor'
    AUTHOR = 'AU'
    EDITOR = 'ED'
    ADVISOR = 'AD'
    CONTRIBUTOR = 'CO'
    TRANSLATOR = 'TR'
    # if Type.Broad.controlled = 'ProvidesSubjectContentAbout'
    SUBJECT = 'SU'
    CATEGORY = 'CA'
    # if Type.Broad.controlled = 'IsInstitutionalHostOf'
    PUBLISHER = 'PU'
    SCHOOL = 'SC'
    INSTITUTION = 'IN'
    MEETING = 'ME'
    # if Type.Broad.controlled = 'IsPublicationHostOf'
    PERIODICAL = 'PE'
    BOOK_SERIES = 'BS'
    TYPE_CHOICES = (
        (AUTHOR, 'Author'),
        (EDITOR, 'Editor'),
        (ADVISOR, 'Advisor'),
        (CONTRIBUTOR, 'Contributor'),
        (TRANSLATOR, 'Translator'),
        (SUBJECT, 'Subject'),
        (CATEGORY, 'Category'),
        (PUBLISHER, 'Publisher'),
        (SCHOOL, 'School'),
        (INSTITUTION, 'Institution'),
        (MEETING, 'Meeting'),
        (PERIODICAL, 'Periodical'),
        (BOOK_SERIES, 'Book Series')
    )
    type_controlled = models.CharField(max_length=2, choices=TYPE_CHOICES,
                                       help_text="""
    Used to specify the nature of the relationship between authority (as the
    subject) and the citation (as the object) more specifically than
    Type.Broad.controlled.""")

    PERSONAL_RESPONS = 'PR'
    SUBJECT_CONTENT = 'SC'
    INSTITUTIONAL_HOST = 'IH'
    PUBLICATION_HOST = 'PH'
    BROAD_TYPE_CHOICES = (
        (PERSONAL_RESPONS, 'Has Personal Responsibility For'),
        (SUBJECT_CONTENT, 'Provides Subject Content About'),
        (INSTITUTIONAL_HOST, 'Is Institutional Host Of'),
        (PUBLICATION_HOST, 'IsPublicationHostOf')
    )
    type_broad_controlled = models.CharField(max_length=2,
                                             choices=BROAD_TYPE_CHOICES,
                                             help_text="""
    Used to specify the nature of the relationship between authority (as the
    subject) and the citation (as the object) more broadly than
    Type.controlled""")

    type_free = models.CharField(max_length=255, help_text="""
    Free text description of the role that the authority plays in the
    citation (e.g. 'introduction by', 'dissertation supervisor', etc)""")

    name_for_display_in_citation = models.CharField(max_length=255,
                                                    help_text="""
    Display for the authority as it is to be used when being displayed with the
    citation. Eg. the form of the author's name as it appears on a
    publication--say, J.E. Koval--which might be different from the name of the
    authority--Jenifer Elizabeth Koval.""")

    # currently not used
    confidence_measure = models.FloatField(default=1.0,
                                           validators = [MinValueValidator(0),
                                                         MaxValueValidator(1)],
                                           help_text="""
    Currently not used: will be used to assess the confidence of the link in the
    event that there is some ambiguity.
    """)

    relationship_weight = models.FloatField(default=1.0,
                                            validators = [MinValueValidator(0),
                                                          MaxValueValidator(2)],
                                            help_text="""
    Currently not used: helps to assess how significant this relationship is--to
    be used mostly in marking subjects.""")


class AARelation(ReferencedEntity, CuratedMixin, AttributeMixin):
    # Currently not used, but crucial to development of next generation relationship tools:
    name = models.CharField(max_length=255, blank=True)
    # Currently not used, but crucial to development of next generation relationship tools:
    description = models.TextField()

    IDENTICAL_TO = 'IDTO'
    PARENT_OF = 'PAOF'
    PREVIOUS_TO = 'PRETO'
    OFFICER_OF = 'OFOF'
    ASSOCIATED_WITH = 'ASWI'
    TYPE_CHOICES = (
        (IDENTICAL_TO, 'Is Identical To'),
        (PARENT_OF, 'Is Parent Of'),
        (PREVIOUS_TO, 'Happened Previous To'),
        (OFFICER_OF, 'Is Officer Of'),
        (ASSOCIATED_WITH, 'Is Associated With')
    )
    type_controlled = models.CharField(max_length=5, choices=TYPE_CHOICES,
                                       help_text="""
    Controlled term specifying the nature of the relationship
    (the predicate between the subject and object).""")

    type_free = models.CharField(max_length=255, blank=True, help_text="""
    Free text description of the relationship.""")

    subject = models.ForeignKey('Authority', related_name='relations_from')
    object = models.ForeignKey('Authority', related_name='relations_to')

    # missing from Stephen's list: objectType, subjectType


class CCRelation(ReferencedEntity, CuratedMixin, AttributeMixin):
    history = HistoricalRecords()

    name = models.CharField(max_length=255, blank=True)

    description = models.TextField(blank=True)

    INCLUDES_CHAPTER = 'IC'
    INCLUDES_SERIES_ARTICLE = 'ISA'
    REVIEW_OF = 'RO'
    RESPONDS_TO = 'RE'
    ASSOCIATED_WITH = 'AS'
    TYPE_CHOICES = (
        (INCLUDES_CHAPTER, 'Includes Chapter'),
        (INCLUDES_SERIES_ARTICLE, 'Includes Series Article'),
        (REVIEW_OF, 'Is Review Of'),
        (RESPONDS_TO, 'Responds To'),
        (ASSOCIATED_WITH, 'Is Associated With')
    )
    type_controlled = models.CharField(max_length=3, choices=TYPE_CHOICES,
                                       help_text="""
    Type of relationship between two citation records.""")

    type_free = models.CharField(max_length=255, blank=True, help_text="""
    Type of relationship as used in the citation.""")

    subject = models.ForeignKey('Citation', related_name='relations_from')
    object = models.ForeignKey('Citation', related_name='relations_to')


class Attribute(ReferencedEntity, CuratedMixin):
    history = HistoricalRecords()

    description = models.TextField(blank=True)

    value = FlexField()
    type_controlled = models.CharField(max_length=255)
    type_controlled_broad = models.CharField(max_length=255, blank=True)
    type_free = models.CharField(max_length=255, blank=True)

    date_iso = models.DateField(blank=True, null=True)
    place = models.ForeignKey('Place', blank=True, null=True)


class PartDetails(models.Model):
    """
    New field: contains volume, issue, page information for works that are parts
    of larger works.
    """
    volume = models.CharField(max_length=255, blank=True)
    volume_free_text = models.CharField(max_length=255, blank=True)
    volume_begin = models.IntegerField(blank=True, null=True)
    volume_end = models.IntegerField(blank=True, null=True)
    issue_free_text = models.CharField(max_length=255, blank=True)
    issue_begin = models.IntegerField(blank=True, null=True)
    issue_end = models.IntegerField(blank=True, null=True)
    pages_free_text = models.CharField(max_length=255, blank=True)
    page_begin = models.IntegerField(blank=True, null=True)
    page_end = models.IntegerField(blank=True, null=True)

    sort_order = models.IntegerField(default=0, help_text="""
    New field: provides a sort order for works that are part of a larger work.
    """)


class Place(models.Model):
    name = models.CharField(max_length=255)
    gis_location = models.ForeignKey('Location', blank=True, null=True)
    gis_schema = models.ForeignKey('LocationSchema', blank=True, null=True)


class LocationSchema(models.Model):
    """
    Represents an SRID.
    """

    name = models.CharField(max_length=255)


class Location(models.Model):
    """
    SRID-agnostic decimal coordinate.
    """

    NORTH = 'N'
    SOUTH = 'S'
    EAST = 'E'
    WEST = 'W'
    LAT_CARDINAL = (
        (NORTH, 'North'),
        (SOUTH, 'South')
    )
    LON_CARDINAL = (
        (EAST, 'East'),
        (WEST, 'West')
    )
    latitude = models.FloatField()
    latitude_direction = models.CharField(max_length=1, choices=LAT_CARDINAL)

    longitude = models.FloatField()
    longitude_direction = models.CharField(max_length=1, choices=LON_CARDINAL)


class LinkedData(ReferencedEntity, CuratedMixin, AttributeMixin):
    history = HistoricalRecords()

    description = models.TextField(blank=True)

    universal_resource_name = models.CharField(max_length=255, help_text="""
    The value of the identifier (the actual DOI link or the value of the ISBN,
    etc). Will be a URN, URI, URL, or other unique identifier for a work, used
    as needed to provide information about how to find the digital object on the
    web or to identify the physical object uniquely.""")

    # In the Admin, we should limit the queryset to Authority and Citation
    #  instances only.
    subject = models.ForeignKey('ReferencedEntity',
                                related_name='linkeddata_entries')

    DOI = 'DOI'         # TODO: Should we represent these choices as a separate
    ISBN = 'ISBN'       #  model, so that they can be extended from the admin
    ISSN = 'ISSN'       #  interface?
    VIAF = 'VIAF'
    TYPE_CHOICES = (
        (DOI, 'DOI'),
        (ISBN, 'ISBN'),
        (ISSN, 'ISSN'),
        (VIAF, 'VIAF')
    )
    type_controlled = models.CharField(max_length=4, choices=TYPE_CHOICES,
                                       help_text="""Type of linked resource.""")
    # is this being used?
    type_controlled_broad = models.CharField(max_length=255, blank=True)
    type_free = models.CharField(max_length=255, blank=True)


class Tracking(CuratedMixin):
    history = HistoricalRecords()

    tracking_info = models.CharField(max_length=255, blank=True)

    HSTM_UPLOAD = 'HS'
    PRINTED = 'PT'
    AUTHORIZED = 'AU'
    PROOFED = 'PD'
    FULLY_ENTERED = 'FU'
    TYPE_CHOICES = (
        (HSTM_UPLOAD, 'HSTM Upload'),
        (PRINTED, 'Printed'),
        (AUTHORIZED, 'Authorized'),
        (PROOFED, 'Proofed'),
        (FULLY_ENTERED, 'Fully Entered'),
    )

    type_controlled = models.CharField(max_length=2, choices=TYPE_CHOICES)

    subject = models.ForeignKey('ReferencedEntity',
                                related_name='tracking_info')

    notes = models.TextField(blank=True)
