from django import template
from isisdata.models import *

register = template.Library()

@register.filter(name='to_class_name')
def to_class_name(value):
    return value.__class__.__name__

@register.filter(name='joinby')
def joinby(value, arg):
    if arg == None or not arg:
        return ''
    try:
        return arg.join(value)
    except:
        return arg

@register.filter
def get_authors(value):
    if value:
        return value.acrelation_set.filter(type_controlled__in=['AU', 'CO'])
    return value

# QUESTION: what URIs do we use?
@register.filter
def get_uri(entry):
    host = "http://isiscb-develop.aplacecalledup.com/isis/"
    if to_class_name(entry) == 'Authority':
        return host + "authority/" + entry.id
    if to_class_name(entry) == 'Citation':
        return host + "citation/" + entry.id
    return ""

@register.filter
def get_title(citation):
    # if citation is not a review simply return title
    if not citation.type_controlled == 'RE':
        if not citation.title:
            return "Title missing"
        return citation.title

    # if citation is a review build title from reviewed citation
    reviewed_books = CCRelation.objects.filter(subject_id=citation.id, type_controlled='RO')

    # sometimes RO relationship is not specified then use inverse reviewed by
    book = None
    if not reviewed_books:
        reviewed_books = CCRelation.objects.filter(object_id=citation.id, type_controlled='RB')
        if reviewed_books:
            book = reviewed_books[0].subject
    else:
        book = reviewed_books[0].object

    if book == None:
        return "Review of unknown publication"



    return 'Review of "' + book.title + '"'
