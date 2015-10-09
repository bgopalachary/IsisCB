from django import template
from isisdata.models import *
from app_filters import *

register = template.Library()

@register.filter
def get_coins_dict(citation):
    metadata_dict = {}

    for linked_data in citation.linkeddata_entries.all():
        if linked_data.type_controlled.name == 'DOI':
            metadata_dict['rft_id'] = ['info:doi/' + linked_data.universal_resource_name]
        if linked_data.type_controlled.name == 'ISBN':
            metadata_dict['rft.isbn'] = [linked_data.universal_resource_name]

    metadata_dict['rft_val_fmt'] = ['info:ofi/fmt:kev:mtx:journal']
    if citation.type_controlled == 'BO':
        metadata_dict['rft_val_fmt'] = ['info:ofi/fmt:kev:mtx:book']
    if citation.type_controlled == 'TH':
        metadata_dict['rft_val_fmt'] = ['info:ofi/fmt:kev:mtx:dissertation']
    #metadata_dict['rft.genre'] = 'article'
    metadata_dict['rft.title'] = [bleach_safe(get_title(citation))]

    authors = citation.acrelation_set.filter(type_controlled__in=['AU'])
    metadata_dict['rft.au'] = []
    for author in authors:
        metadata_dict['rft.au'].append(author.authority.name)

    metadata_dict['rft.date'] = [get_pub_year(citation)]
    return metadata_dict

@register.filter
def get_metatag_fields(citation):
    metadata_dict = {}

    for linked_data in citation.linkeddata_entries.all():
        if linked_data.type_controlled.name == 'DOI':
            metadata_dict['citation_doi'] = [linked_data.universal_resource_name]
        if linked_data.type_controlled.name == 'ISBN':
            metadata_dict['citation_isbn'] = [linked_data.universal_resource_name]

    metadata_dict['citation_title'] = [bleach_safe(get_title(citation))]

    authors = citation.acrelation_set.filter(type_controlled__in=['AU'])
    metadata_dict['citation_author'] = []
    for author in authors:
        metadata_dict['citation_author'].append(author.authority.name)
    metadata_dict['citation_publication_date'] = [get_pub_year(citation)]
    metadata_dict['citation_abstract'] = [bleach_safe(citation.abstract)]

    publisher = citation.acrelation_set.filter(type_controlled__in=['PU'])
    metadata_dict['citation_publisher'] = []
    for pub in publisher:
        metadata_dict['citation_publisher'].append(pub.authority.name)
    metadata_dict['dc.type'] = [citation.get_type_controlled_display]

    periodicals = citation.acrelation_set.filter(type_controlled__in=['PE'])
    metadata_dict['citation_journal_title'] = []
    if periodicals:
        for peri in periodicals:
            metadata_dict['citation_journal_title'].append(peri.authority.name)

    schools = citation.acrelation_set.filter(type_controlled__in=['SC'])
    metadata_dict['citation_dissertation_institution'] = []
    if schools:
        for school in schools:
            metadata_dict['citation_dissertation_institution'] = [school.authority.name]

    if citation.part_details.volume:
        metadata_dict['citation_volume'] = [citation.part_details.volume]
    elif citation.part_details.volume_free_text:
        metadata_dict['citation_volume'] = [citation.part_details.volume_free_text]

    if citation.part_details.issue_begin:
        metadata_dict['citation_issue'] = [str(citation.part_details.issue_begin)]
    if citation.part_details.issue_end:
        metadata_dict['citation_issue'] += " - " + [str(citation.part_details.issue_end)]

    if citation.part_details.page_begin:
        metadata_dict['citation_firstpage'] = [str(citation.part_details.page_begin)]
    if citation.part_details.page_end:
        metadata_dict['citation_lastpage'] = [str(citation.part_details.page_end)]

    metadata_dict['citation_language'] = []
    if citation.language.all():
        for lang in citation.language.all():
            metadata_dict['citation_language'] = [lang.id]

    return metadata_dict