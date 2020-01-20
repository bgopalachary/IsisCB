"""
Module for bulk-exporting IsisCB data in EBSCO format.

The strategy here is to favor extensibility/flexibility in defining output
columns, at the expense of performance. The performance hit is probably OK,
since these jobs will be performed asynchronously.
"""

from isisdata.models import *
from django.utils.text import slugify
import functools
import export_item_count_csv
from django.conf import settings


def _authors_editors_names(obj, extra, config={}):
    fields = ['authority__id', 'authority__name', 'type_controlled']
    names = obj.acrelation_set.filter(type_controlled__in=[ACRelation.EDITOR, ACRelation.AUTHOR])\
                                   .order_by('data_display_order')\
                                   .values_list(*fields)
    return u' // '.join(map(lambda x: "AuthorityID %s || AuthorityName %s || Role %s"%(x[0], x[1], dict(ACRelation.TYPE_CHOICES)[x[2]]), names))

def _publisher_school(obj, extra, config={}):
    if obj.type_controlled in [Citation.BOOK, Citation.CHAPTER]:
        obj_with_publisher = obj
        # if we have a chapter we need to get the connect book
        if obj.type_controlled == Citation.CHAPTER:
            book_ccr = obj.ccrelations.filter(type_controlled__in=[CCRelation.INCLUDES_CHAPTER])
            if book_ccr and book_ccr.first():
                obj = book_ccr.first().subject

        # get publisher
        fields = ['authority__id', 'authority__name']
        names = obj.acrelation_set.filter(type_controlled=ACRelation.PUBLISHER)\
                                       .values_list(*fields)

        return u' // '.join(map(lambda x: "AuthorityID %s || AuthorityName %s"%(x[0], x[1]), names))

    # school
    if obj.type_controlled in [Citation.THESIS]:
        fields = ['authority__id', 'authority__name']
        names = obj.acrelation_set.filter(type_controlled=ACRelation.SCHOOL)\
                                       .values_list(*fields)

        return u' // '.join(map(lambda x: "AuthorityID %s || AuthorityName %s"%(x[0], x[1]), names))

    return ""

def _journal_name(obj, extra, config={}):
    qs = obj.acrelation_set.filter(type_controlled=ACRelation.PERIODICAL)
    if qs.count() == 0:
        return u""
    _first = qs.first()
    if _first.authority:
        return unicode(_first.authority.name)
    return u""

def _volume(obj, extra, config={}):
    if not hasattr(obj, 'part_details') or obj.part_details is None:
        return u""
    # ISISCB-1033
    if obj.part_details.volume_free_text and obj.part_details.volume_free_text.strip():
        return obj.part_details.volume_free_text.strip()

    if obj.part_details.volume_begin or obj.part_details.volume_end:
        return "-".join(map(lambda x: str(x), filter(None, [obj.part_details.volume_begin, obj.part_details.volume_end])))

    return ''

def _pages_free_text(obj, extra, config={}):
    if not getattr(obj, 'part_details', None):
        return u""
    if obj.part_details.pages_free_text and obj.part_details.pages_free_text.strip():
        return obj.part_details.pages_free_text.strip()

    if obj.part_details.page_begin or obj.part_details.page_end:
        return "-".join(map(lambda x: str(x), filter(None, [obj.part_details.page_begin, obj.part_details.page_end])))

    return ''

def _category(obj, extra, config={}):
    fields = ['authority__name']
    names = obj.acrelation_set.filter(type_controlled=ACRelation.CATEGORY)\
                                   .values_list(*fields)
    return u' || '.join(map(lambda x: x[0], names))

def _language(obj, extra, config={}):
    return u' || '.join(filter(lambda o: o is not None, list(obj.language.all().values_list('name', flat=True))))

# check functions
CHECK_WELL_FORMED = "Well-formed"
CHECK_EMPTY = "Empty"
CHECK_NON_STANDARD = "Non-Standard"
CHECK_BROKEN_LINK = "BrokenLink"


def _title_check(obj, extra, config={}):
    if not obj.title and not obj.title.strip():
        return CHECK_EMPTY

    return CHECK_WELL_FORMED

def _author_check(obj, extra, config={}):
    authors = obj.acrelation_set.filter(type_controlled__in=[ACRelation.EDITOR, ACRelation.AUTHOR])
    if not authors:
        return CHECK_EMPTY

    return _check_acrs(authors, [Authority.PERSON])

def _publisher_school_check(obj, extra, config={}):
    acrelations = None
    if obj.type_controlled in [Citation.BOOK, Citation.CHAPTER]:
        obj_with_publisher = obj
        # if we have a chapter we need to get the connect book
        if obj.type_controlled == Citation.CHAPTER:
            book_ccr = obj.ccrelations.filter(type_controlled__in=[CCRelation.INCLUDES_CHAPTER])
            if book_ccr and book_ccr.first():
                obj = book_ccr.first().subject

        # get publisher
        acrelations = obj.acrelation_set.filter(type_controlled=ACRelation.PUBLISHER)

    if obj.type_controlled in [Citation.THESIS]:
        acrelations = obj.acrelation_set.filter(type_controlled=ACRelation.SCHOOL)

    if not acrelations:
        return CHECK_EMPTY

    return _check_acrs(acrelations, [Authority.INSTITUTION])

def _journal_check(obj, extra, config={}):
    journals = obj.acrelation_set.filter(type_controlled=ACRelation.PERIODICAL)
    if not journals:
        return CHECK_EMPTY

    return _check_acrs(journals, [Authority.SERIAL_PUBLICATION])

def _year_check(obj, extra, config={}):
    year = obj.publication_date.year
    if not year:
        return CHECK_EMPTY

    if year < 1970:
        return CHECK_NON_STANDARD

    return CHECK_WELL_FORMED

def _vol_check(obj, extra, config={}):
    vol = _volume(obj, extra, config)
    if not vol:
        return CHECK_EMPTY

    if len(vol) > 9:
        return CHECK_NON_STANDARD

    return CHECK_WELL_FORMED

def _page_check(obj, extra, config={}):
    pages = _pages_free_text(obj, extra, config)
    if not pages:
        return CHECK_EMPTY

    return CHECK_WELL_FORMED

def _lang_check(obj, extra, config={}):
    lang = _language(obj, extra, config)
    if not lang:
        return CHECK_EMPTY

    return CHECK_WELL_FORMED

def _cat_check(obj, extra, config={}):
    categories = obj.acrelation_set.filter(type_controlled=ACRelation.CATEGORY)
    if not categories:
        return CHECK_EMPTY

    if categories.count() > 1 or categories.first().authority.classification_system != Authority.SPWC:
        return CHECK_NON_STANDARD

    return CHECK_WELL_FORMED

def _check_acrs(acrs, authority_types):
    is_non_standard = False
    for acr in acrs:
        if is_broken_link(acr):
            return CHECK_BROKEN_LINK

        if acr.authority.type_controlled not in authority_types:
            is_non_standard = True

    if is_non_standard:
        return CHECK_NON_STANDARD

    return CHECK_WELL_FORMED

def is_broken_link(acr):
    return acr.record_status_value != CuratedMixin.ACTIVE or not acr.authority or acr.authority.record_status_value != CuratedMixin.ACTIVE

object_id = export_item_count_csv.Column(u'Record number', lambda obj, extra, config={}: obj.id)
print_status = export_item_count_csv.Column(u'Print status', export_item_count_csv._print_status)
record_status = export_item_count_csv.Column(u'Record Status', lambda obj, extra, config={}: obj.get_record_status_value_display())
curation_link = export_item_count_csv.Column('Curation Link', export_item_count_csv._curation_link)
public_link = export_item_count_csv.Column('Public Link', export_item_count_csv._public_link)
record_type = export_item_count_csv.Column('Record Type', export_item_count_csv._record_type)
title_check = export_item_count_csv.Column('Title Check', _title_check)
author_check = export_item_count_csv.Column('Auth/Ed Check', _author_check)
publisher_school_check = export_item_count_csv.Column('Pub/Sch Check', _publisher_school_check)
journal_check = export_item_count_csv.Column('Jrnl Check', _journal_check)
year_check = export_item_count_csv.Column('Year Check', _year_check)
vol_check = export_item_count_csv.Column('Vol Check', _vol_check)
page_check = export_item_count_csv.Column('Page Check', _page_check)
lang_check = export_item_count_csv.Column('Lang Check', _lang_check)
cat_check = export_item_count_csv.Column('Cat Check', _cat_check)
citation_title = export_item_count_csv.Column(u'Title', export_item_count_csv._citation_title, Citation)
authors_editors_names = export_item_count_csv.Column('Author/Editor Names', _authors_editors_names)
publisher_school = export_item_count_csv.Column('Publisher/School', _publisher_school)
journal_name = export_item_count_csv.Column("Journal Name", _journal_name)
year_of_publication = export_item_count_csv.Column(u'Year Published', lambda obj, extra, config={}: obj.publication_date.year)
volume = export_item_count_csv.Column(u"Volume", _volume)
pages_free_text = export_item_count_csv.Column(u"Pages", _pages_free_text)
category = export_item_count_csv.Column(u"Category", _category)
language = export_item_count_csv.Column(u"Language", _language)
tracking_records = export_item_count_csv.Column('Tracking Records', export_item_count_csv._tracking_records)
record_action = export_item_count_csv.Column(u'Record Action', lambda obj, extra, config={}: obj.get_record_action_display())
related_citations = export_item_count_csv.Column('Related Citations', export_item_count_csv._related_citations)
staff_notes = export_item_count_csv.Column(u"Staff Notes", lambda obj, extra, config={}: obj.administrator_notes)
record_history = export_item_count_csv.Column(u"Record History", lambda obj, extra, config={}: obj.record_history)
dataset = export_item_count_csv.Column(u"Dataset", export_item_count_csv._dataset)
created_date = export_item_count_csv.Column(u"Created Date", export_item_count_csv._created_date)
modified_date = export_item_count_csv.Column(u"Modified Date",export_item_count_csv. _modified_date)


CITATION_COLUMNS = [
    object_id,
    print_status,
    record_status,
    curation_link,
    public_link,
    record_type,
    title_check,
    author_check,
    publisher_school_check,
    journal_check,
    year_check,
    vol_check,
    page_check,
    lang_check,
    cat_check,
    citation_title,
    authors_editors_names,
    publisher_school,
    journal_name,
    year_of_publication,
    volume,
    pages_free_text,
    category,
    language,
    tracking_records,
    related_citations,
    staff_notes,
    record_history,
    dataset,
    created_date,
    modified_date,
]
