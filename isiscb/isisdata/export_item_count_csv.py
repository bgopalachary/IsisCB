"""
Module for bulk-exporting IsisCB data in EBSCO format.

The strategy here is to favor extensibility/flexibility in defining output
columns, at the expense of performance. The performance hit is probably OK,
since these jobs will be performed asynchronously.
"""

from isisdata.models import *
from django.utils.text import slugify
import functools
from django.conf import settings


def generate_item_count_csv(stream, queryset, columns):
    """
    Write data from a queryset as CSV to a file/stream.

    Note: this is for synchronous export only. An asynchronous implementation
    can be found in :mod:`isisdata.tasks`\.

    Parameters
    ----------
    stream : object
        A file pointer, or anything that provides a ``write()`` method.
    queryset : iterable
        Each object yielded will be passed to the column handlers in
        ``columns``.
    columns : list
        Should be a list of :class:`.Column` instances.
    """

    import unicodecsv as csv
    writer = csv.writer(stream)
    writer.writerow(map(lambda c: c.label, columns))
    extra = []
    for obj in queryset:
        if obj is not None:
            writer.writerow(map(lambda c: c(obj, extra), columns))

    for obj in extra:
        if obj is not None:
            writer.writerow(map(lambda c: c(obj, []), columns))


class Column(object):
    """
    Convenience wrapper for functions that generate column data.

    Parameters
    ----------
    label : str
        Label used as the column header in the output document.
    fnx : callable
        Should take a single object (e.g. a model instance), and return unicode.
    model : class
        Optional. If provided, an AssertionError will be raised if the column
        is passed an object that is not an instance of ``model``.
    """
    def __init__(self, label, fnx, model=None):
        assert hasattr(fnx, '__call__')
        self.label = label
        self.call = fnx
        self.model = model
        self.slug = slugify(label)

    def __call__(self, obj, extra, config={}):
        try:
            if self.model is not None:
                assert isinstance(obj, self.model)
            return self.call(obj, extra, config)
        except AssertionError as E:    # Let this percolate through.
            raise E
        except Exception as E:
            print 'Exception in column %s for object %s' % (self.label, getattr(obj, 'id', None))
            print E
            return u""


def _print_status(obj, extra, config={}):
    _q = Q(record_status_value=CuratedMixin.ACTIVE) \
         & Q(authority__type_controlled=Authority.CLASSIFICATION_TERM)
    category = obj.acrelation_set.filter(_q)

    tracking_records_proofed = obj.tracking_records.filter(type_controlled=Tracking.PROOFED)
    tracking_records_printed = obj.tracking_records.filter(type_controlled=Tracking.PRINTED)

    if tracking_records_printed:
        return "AlreadyPrinted"
    if obj.record_status_value == CuratedMixin.ACTIVE and tracking_records_proofed and category:
        return "Print Classified"
    if obj.record_status_value == CuratedMixin.ACTIVE and tracking_records_proofed and not category:
        return "Print NotClassified"

    return "NotReady"

def _curation_link(obj, extra, config={}):
    return settings.URI_PREFIX + 'curation/citation/' + obj.id

def _public_link(obj, extra, config={}):
    return settings.URI_PREFIX + 'citation/' + obj.id

def _citation_title(obj, extra, config={}):
    """
    Get the production title for a citation.
    """
    # if citation is not a review simply return title
    if not obj.type_controlled == Citation.REVIEW:
        if not obj.title:
            return u"Title missing"
        return obj.title

    # if citation is a review build title from reviewed citation
    reviewed_books = obj.relations_from.filter(type_controlled=CCRelation.REVIEW_OF)

    # sometimes RO relationship is not specified then use inverse reviewed by
    book = None
    if not reviewed_books:
        reviewed_books = obj.relations_to.filter(type_controlled=CCRelation.REVIEWED_BY)
        if reviewed_books:
            book = reviewed_books.first().subject
    else:
        book = reviewed_books.first().object

    if book is None:
        return u"Review of unknown publication"
    return u'Review of "%s"' % book.title

def _record_type(obj, extra, config={}):
    main_type = obj.get_type_controlled_display()
    if obj.subtype:
        return "%s || %s"%(main_type, obj.subtype.name)
    return main_type

def _tracking_records(obj, extra, config={}):
    records = obj.tracking_records.all()
    return " // ".join([r.get_type_controlled_display() for r in records])

def _related_citations(obj, extra, config={}):
    qs_from = obj.relations_from.all()
    qs_to = obj.relations_to.all()

    fields_object = _get_metadata_fields_citation(config, 'object')
    fields_subject = _get_metadata_fields_citation(config, 'subject')

    return u' // '.join(map(functools.partial(create_ccr_string), qs_from.values_list(*fields_object)) + map(functools.partial(create_ccr_string), qs_to.values_list(*fields_subject)))

def _get_metadata_fields_citation(config, type):
    ccr_fields = ['id',
              'record_status_value',
              'type_controlled',
              type + '__id',
              type + '__record_status_value',
              type + '__type_controlled',
              type + '__title'
             ]
    return ccr_fields


def create_ccr_string(ccr, delimiter=u" || "):
    fields = ['CCRType ' + dict(CCRelation.TYPE_CHOICES)[ccr[2]],
               'CitationType ' + dict(Citation.TYPE_CHOICES)[ccr[5]],
               'CitationID ' + str(ccr[3]),
              ]
    return delimiter.join(fields)

def _dataset(obj, extra, config={}):
    if not obj.belongs_to:
        return u""

    return obj.belongs_to.name

def _created_date(obj, extra, config={}):
    date = u""
    try:
        if type(obj) == Citation:
            date = obj.created_native if obj.created_native else ""
        else:
            date = obj.created_on_stored if obj.created_on_stored else ""
    except:
        pass

    return unicode(date)[:10] + " || " + (obj.created_by_native.username if obj.created_by_native else "")

def _modified_date(obj, extra, config={}):
    date = u""
    try:
        date = obj._history_date if obj._history_date else ""
    except:
        pass

    return unicode(date)[:10] + " || " + (obj.modified_by.username if obj.modified_by else "")

object_id = Column(u'Record number', lambda obj, extra, config={}: obj.id)
print_status = Column(u'Print status', _print_status)
record_status = Column(u'Record Status', lambda obj, extra, config={}: obj.get_record_status_value_display())
curation_link = Column('Curation Link', _curation_link)
public_link = Column('Public Link', _public_link)
citation_title = Column(u'Title', _citation_title, Citation)
record_type = Column('Record Type', _record_type)
tracking_records = Column('Tracking Records', _tracking_records)
record_action = Column(u'Record Action', lambda obj, extra, config={}: obj.get_record_action_display())
related_citations = Column('Related Citations', _related_citations)
staff_notes = Column(u"Staff Notes", lambda obj, extra, config={}: obj.administrator_notes)
record_history = Column(u"Record History", lambda obj, extra, config={}: obj.record_history)
dataset = Column(u"Dataset", _dataset)
created_date = Column(u"Created Date", _created_date)
modified_date = Column(u"Modified Date", _modified_date)


CITATION_COLUMNS = [
    object_id,
    print_status,
    record_status,
    curation_link,
    public_link,
    record_type,
    citation_title,
    tracking_records,
    related_citations,
    staff_notes,
    record_history,
    dataset,
    created_date,
    modified_date,
]
