from django import template
from isisdata.models import *
from app_filters import *

register = template.Library()

@register.filter
def get_coins_dict(citation):
    metadata_dict = {}
    #metadata_dict['rft_val_fmt'] = 'info:ofi/fmt:kev:mtx:book'
    metadata_dict['dc.genre'] = 'book'
    metadata_dict['dc.title'] = bleach_safe(get_title(citation))
    for author in get_contributors(citation):
        metadata_dict['dc.creator'] = contributor_as_string(author)
    return metadata_dict

@register.filter
def get_metatag_fields(citation):
    metadata_dict = {}

    for linked_data in citation.linkeddata_entries.all():
        if linked_data.type_controlled.name == 'DOI':
            metadata_dict['citation_doi'] = linked_data.universal_resource_name
        if linked_data.type_controlled.name == 'ISBN':
            metadata_dict['citation_isbn'] = linked_data.universal_resource_name

    metadata_dict['citation_title'] = bleach_safe(get_title(citation))
    authors = citation.acrelation_set.filter(type_controlled__in=['AU'])
    for author in authors:
        metadata_dict['citation_author'] = author.authority.name
    metadata_dict['citation_publication_date'] = get_pub_year(citation)
    metadata_dict['citation_abstract'] = bleach_safe(citation.abstract)

    publisher = citation.acrelation_set.filter(type_controlled__in=['PU'])
    for pub in publisher:
        metadata_dict['citation_publisher'] = pub.authority.name
    metadata_dict['dc.type'] = citation.get_type_controlled_display

    periodicals = citation.acrelation_set.filter(type_controlled__in=['PE'])
    if periodicals:
        for peri in periodicals:
            metadata_dict['citation_journal_title'] = peri.authority.name

    schools = citation.acrelation_set.filter(type_controlled__in=['SC'])
    if schools:
        for school in schools:
            metadata_dict['citation_dissertation_institution'] = school.authority.name

    if citation.part_details.volume:
        metadata_dict['citation_volume'] = citation.part_details.volume
    elif citation.part_details.volume_free_text:
        metadata_dict['citation_volume'] = citation.part_details.volume_free_text

    if citation.part_details.issue_begin:
        metadata_dict['citation_issue'] = str(citation.part_details.issue_begin)
    if citation.part_details.issue_end:
        metadata_dict['citation_issue'] += " - " + str(citation.part_details.issue_end)

    if citation.part_details.page_begin:
        metadata_dict['citation_firstpage'] = str(citation.part_details.page_begin)
    if citation.part_details.page_end:
        metadata_dict['citation_lastpage'] = str(citation.part_details.page_end)

    if citation.language.all():
        for lang in citation.language.all():
            metadata_dict['citation_language'] = lang.id

    return metadata_dict
