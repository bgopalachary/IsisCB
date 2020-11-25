from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from django import template
from isisdata.models import *
from isisdata.templatetags.app_filters import *
import urllib.request, urllib.parse, urllib.error
import re
import numpy
import csv
import json

register = template.Library()

@register.filter
def get_authority_name(id):
    try:
        authority = Authority.objects.get(id=id)
        name = authority.name
    except:
        name = id
    return name

@register.filter
def get_visual(auth1, auth2):
    #code
    c1=Citation.objects.filter(public=True, acrelation__public=True, acrelation__authority__public=True, acrelation__authority_id=auth2).filter(acrelation__authority_id=auth1, acrelation__type_broad_controlled=ACRelation.PERSONAL_RESPONS, acrelation__data_display_order__lt=30, acrelation__public=True, acrelation__authority__public=True).distinct()
    years = []
    for c in c1.all():
        if c.publication_date:
            years.append(c.publication_date.year)
    counts,bins = numpy.histogram(years , bins=6 , range=(1970,2030))
    bins = bins.astype('int32')
    z = dict(zip(bins , counts))
    new = [{"type": f, "count": k} for f,k in z.items()] 
    #print(new)
    return new

@register.filter
def get_cat(auth1, auth2):
    #code
    c2=Citation.objects.filter(acrelation__authority_id=auth2).filter(acrelation__authority_id=auth1, acrelation__type_controlled=ACRelation.CATEGORY)
    #, acrelation__public=True, acrelation__authority__public=True).distinct()
    years = []
    for c in c2.all():
        if c.publication_date:
            years.append(c.publication_date.year)
    counts,bins = numpy.histogram(years , bins=6 , range=(1970,2030))
    bins = bins.astype('int32')
    z = dict(zip(bins , counts))
    new1 = [{"type": f, "count": k} for f,k in z.items()] 
    #print(new1)
    return new1

@register.filter
def get_pub(auth1, auth2):
    #code
    c2=Citation.objects.filter(acrelation__authority_id=auth2).filter(acrelation__authority_id=auth1, acrelation__type_controlled=ACRelation.PUBLISHER)
    #, acrelation__public=True, acrelation__authority__public=True).distinct()
    years = []
    for c in c2.all():
        if c.publication_date:
            years.append(c.publication_date.year)
    counts,bins = numpy.histogram(years , bins=6 , range=(1970,2030))
    bins = bins.astype('int32')
    z = dict(zip(bins , counts))
    new1 = [{"type": f, "count": k} for f,k in z.items()] 
    #print(new1)
    return new1

@register.filter
def get_journal(auth1, auth2):
    #code
    c2=Citation.objects.filter(acrelation__authority_id=auth2).filter(acrelation__authority_id=auth1, acrelation__type_controlled=ACRelation.PERIODICAL)
    #, acrelation__public=True, acrelation__authority__public=True).distinct()
    years = []
    for c in c2.all():
        if c.publication_date:
            years.append(c.publication_date.year)
    counts,bins = numpy.histogram(years , bins=6 , range=(1970,2030))
    bins = bins.astype('int32')
    z = dict(zip(bins , counts))
    new1 = [{"type": f, "count": k} for f,k in z.items()] 
    #print(new1)
    return new1

@register.filter
def get_con(auth1, auth2):
    #code
    c2=Citation.objects.filter(acrelation__authority_id=auth2).filter(acrelation__authority_id=auth1, acrelation__authority__type_controlled=Authority.CONCEPT)
    #, acrelation__public=True, acrelation__authority__public=True).distinct()
    years = []
    for c in c2.all():
        if c.publication_date:
            years.append(c.publication_date.year)
    counts,bins = numpy.histogram(years , bins=6 , range=(1970,2030))
    bins = bins.astype('int32')
    z = dict(zip(bins , counts))
    new1 = [{"type": f, "count": k} for f,k in z.items()] 
    #print(new1)
    return new1

@register.filter
def get_peo(auth1, auth2):
    #code
    c2=Citation.objects.filter(acrelation__authority_id=auth2).filter(acrelation__authority_id=auth1, acrelation__authority__type_controlled=Authority.PERSON)
    #, acrelation__public=True, acrelation__authority__public=True).distinct()
    years = []
    for c in c2.all():
        if c.publication_date:
            years.append(c.publication_date.year)
    counts,bins = numpy.histogram(years , bins=6 , range=(1970,2030))
    bins = bins.astype('int32')
    z = dict(zip(bins , counts))
    new1 = [{"type": f, "count": k} for f,k in z.items()] 
    #print(new1)
    return new1

@register.filter
def get_in(auth1, auth2):
    #code
    c2=Citation.objects.filter(acrelation__authority_id=auth2).filter(acrelation__authority_id=auth1, acrelation__authority__type_controlled=Authority.INSTITUTION)
    #, acrelation__public=True, acrelation__authority__public=True).distinct()
    years = []
    for c in c2.all():
        if c.publication_date:
            years.append(c.publication_date.year)
    counts,bins = numpy.histogram(years , bins=6 , range=(1970,2030))
    bins = bins.astype('int32')
    z = dict(zip(bins , counts))
    new1 = [{"type": f, "count": k} for f,k in z.items()] 
    #print(new1)
    return new1

@register.filter
def get_pla(auth1, auth2):
    #code
    c2=Citation.objects.filter(acrelation__authority_id=auth2).filter(acrelation__authority_id=auth1, acrelation__authority__type_controlled=Authority.GEOGRAPHIC_TERM)
    #, acrelation__public=True, acrelation__authority__public=True).distinct()
    years = []
    for c in c2.all():
        if c.publication_date:
            years.append(c.publication_date.year)
    counts,bins = numpy.histogram(years , bins=6 , range=(1970,2030))
    bins = bins.astype('int32')
    z = dict(zip(bins , counts))
    new1 = [{"type": f, "count": k} for f,k in z.items()] 
    #print(new1)
    return new1

@register.filter
def get_times(auth1, auth2):
    #code
    c2=Citation.objects.filter(acrelation__authority_id=auth2).filter(acrelation__authority_id=auth1, acrelation__authority__type_controlled=Authority.TIME_PERIOD)
    #, acrelation__public=True, acrelation__authority__public=True).distinct()
    years = []
    for c in c2.all():
        if c.publication_date:
            years.append(c.publication_date.year)
    counts,bins = numpy.histogram(years , bins=6 , range=(1970,2030))
    bins = bins.astype('int32')
    z = dict(zip(bins , counts))
    new1 = [{"type": f, "count": k} for f,k in z.items()] 
    #print(new1)
    return new1


    

@register.filter
def set_excluded_facets(url, available_facets):
    facets = list(available_facets)
    exclude_str = ""
    for facet in facets:
        facet_tuple = tuple(facet)
        if 'selected_facets=citation_type:'+facet_tuple[0] not in url:
            exclude_str += 'excluded_facets=citation_type:' + facet_tuple[0] + "&"
    return (url+ '&' + exclude_str).replace("&&", "&")

@register.filter
def remove_url_part(url, arg):
    return url.replace(arg, "").replace("&&", "&")

@register.filter
def add_selected_facet(url, facet):
    return (url + "&selected_facets=" + urllib.parse.unquote(facet)).replace("&&", "&")

@register.filter
def add_facet_or_operator(url):
    op = 'facet_operators=type:or'
    if op not in url:
        url = url + '&' + op
    return url.replace('&&', '&')

@register.filter
def add_excluded_citation_type_facet(url, facet):
    facet_str = 'citation_type:' + urllib.parse.quote(facet)
    if 'selected_facets=' + facet_str in url:
        url = url.replace('selected_facets=' + facet_str, '')
    url = url + '&excluded_facets=' + facet_str
    return url.replace('&&', '&')

@register.filter
def add_excluded_facet(url, facet):
    if 'selected_facets=' + facet in url:
        url = url.replace('selected_facets=' + facet, '')
    url = url + '&excluded_facets=' + facet
    return url.replace('&&', '&')

@register.filter
def remove_all_type_facets(url, facet_type):
    url = re.sub(r"selected_facets=" + facet_type + ":.+?&", "", url).replace('&&', '&')
    return re.sub(r"excluded_facets=" + facet_type + ":.+?&", "", url).replace('&&', '&')

@register.filter
def create_facet_with_field(facet, field):
    return field + ":" + facet

@register.filter
def are_reviews_excluded(url):
    return 'excluded_facets=citation_type:Review' in url
