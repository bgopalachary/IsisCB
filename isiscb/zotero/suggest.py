from __future__ import division
from __future__ import unicode_literals
from builtins import zip
from builtins import range
from past.utils import old_div
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType


from isisdata.models import *
from zotero.models import *

import difflib
from collections import Counter, defaultdict

import regex


def argsort(seq):
    seq = list(seq)
    return sorted(list(range(len(seq))), key=seq.__getitem__)


def aggregate_hits(hits):
    """
    Combine individual hits into a condensed set of suggestions and reasons.
    """
    uniqueHits = Counter()
    uniqueReasons = defaultdict(list)
    for hit, basis, value, match in hits:
        uniqueHits[hit] += match
        uniqueReasons[hit].append((basis, value))

    for key, value in list(uniqueHits.items()):
        uniqueHits[key] = old_div(value,float(len(uniqueReasons[key])))

    return [{
                'id': list(uniqueHits.keys())[k],
                'match': uniqueHits[list(uniqueHits.keys())[k]],
                'reasons': uniqueReasons[list(uniqueHits.keys())[k]]
            } for k in argsort(list(uniqueHits.values()))[::-1]]


def suggest_by_attributes(draftObject):
    hits = []
    for attribute in draftObject.attributes.all():
        attrTypes = AttributeType.objects.filter(name__icontains=attribute.name)
        for attrType in attrTypes:
            exact_match = attrType.attribute_set.filter(value__value=attribute.value)
            hits += [(attr.subject_instance_id, 'Attribute', attr.id, 1.0) for attr in exact_match]
    return hits


def suggest_authority_by_resolutions(draftAuthority):
    """
    Suggest production :class:`isisdata.Authority` instances for a
    :class:`zotero.DraftAuthority` based on prior
    :class:`zotero.InstanceResolutionEvent`\s.
    """
    hits = []

    # Find similar DraftAuthority instances.
    fuzzy_names = Q(name_for_sort__icontains=draftAuthority.name) | Q(name_for_sort__in=draftAuthority.name)
    for v in draftAuthority.name.split(' '):    # Look at parts of the name.
        if len(v) > 2:
            # startswith is about as broad as we can go without getting flooded
            #  by extraneous results.
            fuzzy_names |= Q(name_for_sort__istartswith=v)
    queryset = DraftAuthority.objects.filter(processed=True).filter(fuzzy_names)

    resolutions = defaultdict(list)
    for resolvedAuthority in queryset:
        # Just in case we marked this DraftAuthority resolved without creating
        #  a corresponding InstanceResolutionEvent.
        if resolvedAuthority.resolutions.count() == 0:
            continue

        # SequenceMatcher.quick_ratio gives us a rough indication of the
        #  similarity between the two authority names.
        match = difflib.SequenceMatcher(None, draftAuthority.name,
                                        resolvedAuthority.name).quick_ratio()
        if match > 0.6:     # This is an arbitrary threshold.
            resolution = resolvedAuthority.resolutions.first()
            resolutions[resolution.to_instance.id].append((resolvedAuthority.name, match))

    if len(resolutions) == 0:
        return []

    N = sum([len(instances) for instances in list(resolutions.values())])
    N_matches = {}
    scores = {}
    for resolution_target, instances in list(resolutions.items()):
        N_instances = float(len(instances))
        N_matches[resolution_target] = N_instances
        scores[resolution_target] = old_div(sum(zip(*instances)[1]),N_instances)

    max_matches = max(N_matches.values())

    for resolution_target, score in list(scores.items()):
        score_normed = score * N_matches[resolution_target]/max_matches
        hits.append((resolution_target, 'Resolution', 'name', score_normed))

    return hits


def suggest_by_linkeddata(draftObject):
    """
    Attempt to match an object based on associated linkeddata values.
    """
    hits = []
    for linkeddata in draftObject.linkeddata.all():
        ldTypes = LinkedDataType.objects.filter(name__icontains=linkeddata.name)
        for ldType in ldTypes:
            exact_match = ldType.linkeddata_set.filter(universal_resource_name__icontains=linkeddata.value)
            hits += [(ldatum.subject_instance_id, 'LinkedData', ldatum.id, 1.0) for ldatum in exact_match]

        inexact_match = LinkedData.objects.filter(
           Q(universal_resource_name__icontains=linkeddata.value) |
           Q(universal_resource_name__in=linkeddata.value))
        if inexact_match.count() <= 10:
            for ldatum in inexact_match:
                match = difflib.SequenceMatcher(None, ldatum.universal_resource_name, linkeddata.value).quick_ratio()
                if match > 0.6:
                    hits.append((ldatum.subject_instance_id, 'LinkedData', ldatum.id, match))

    return hits


def suggest_by_field(draftObject, field, targetModel, targetField, scramble=False):
    """
    Attempt to match an object based on an arbitrary field.
    """
    hits = []
    value = getattr(draftObject, field)


    def remove_punctuation(text):
        return regex.sub(ur"\p{P}+", "", text)

    if isinstance(value, str) or isinstance(value, str):
        value = remove_punctuation(value)

    q = Q()
    q |= Q(**{'{0}__icontains'.format(targetField): value})
    q |= Q(**{'{0}__in'.format(targetField): value})
    if scramble:
        for v in value.split(' '):
            if len(v) > 2:
                q |= Q(**{'{0}__istartswith'.format(targetField): v})

    inexact_match = targetModel.objects.filter(q)

    for obj in inexact_match:
        targetValue = getattr(obj, targetField)
        match = difflib.SequenceMatcher(None, value, targetValue).quick_ratio()

        if match > 0.6:
            hits.append((obj.id, 'field', targetField, match))
    return hits


def suggest_citation(draftCitation):
    hits = []
    hits += suggest_by_linkeddata(draftCitation)
    hits += suggest_by_field(draftCitation, 'title', Citation, 'title')
    return aggregate_hits(hits)


def suggest_authority(draftAuthority):
    hits = []
    hits += suggest_by_linkeddata(draftAuthority)
    hits += suggest_authority_by_resolutions(draftAuthority)
    # hits += suggest_by_attributes(draftAuthority)
    hits += suggest_by_field(draftAuthority, 'name', Authority, 'name_for_sort', scramble=True)
    return aggregate_hits(hits)


# def suggest_citations(queryset):
#     for obj in queryset:
#         print suggest_citation(obj)
#
#
# def suggest_authorities(queryset):
#     for obj in queryset:
#         print suggest_authority(obj)
