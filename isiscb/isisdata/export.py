"""
Module for bulk-exporting IsisCB data.

The strategy here is to favor extensibility/flexibility in defining output
columns, at the expense of performance. The performance hit is probably OK,
since these jobs will be performed asynchronously.
"""

from isisdata.models import *


def generate_csv(stream, queryset, columns):
    import csv
    writer = csv.writer(stream)
    writer.writerow(map(lambda c: c.label, columns))
    for obj in queryset:
        writer.writerow(map(lambda c: c(obj), columns))


class Column(object):
    def __init__(self, label, fnx, model=None):
        assert hasattr(fnx, '__call__')
        self.label = label
        self.call = fnx
        self.model = model

    def __call__(self, obj):
        if self.model is not None:
            assert isinstance(obj, self.model)
        return self.call(obj)


def _citation_title(obj):
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


def _citation_author(obj):
    """
    Get the names of all authors on a citation.
    """
    names = obj.acrelation_set.filter(type_controlled=ACRelation.AUTHOR)\
                                   .order_by('data_display_order')\
                                   .values_list('name_for_display_in_citation',
                                                'authority__name')
    print names
    return u'; '.join(map(lambda o: o[0] if o[0] else o[1], names))


def _citation_editor(obj):
    """
    Get the names of all editors on a citation.
    """
    names = obj.acrelation_set.filter(type_controlled=ACRelation.EDITOR)\
                                   .order_by('data_display_order')\
                                   .values_list('name_for_display_in_citation',
                                                'authority__name')
    return u'; '.join(map(lambda o: o[0] if o[0] else o[1], names))


object_id = Column(u'Record ID', lambda obj: obj.id)
citation_title = Column(u'Title', _citation_title, Citation)
citation_author = Column(u'Author', _citation_author, Citation)
citation_editor = Column(u'Editor', _citation_editor, Citation)
