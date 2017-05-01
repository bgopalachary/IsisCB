from __future__ import absolute_import

from django.contrib.admin.views.decorators import staff_member_required, user_passes_test
from django.contrib import messages

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, QueryDict #, HttpResponseForbidden, Http404, , JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.core.urlresolvers import reverse
from django.core.cache import caches
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.utils import formats
from django.utils.http import urlencode
from django.utils.text import slugify
from django.template.loader import get_template

from rules.contrib.views import permission_required, objectgetter
from .rules import is_accessible_by_dataset
from django.forms import modelform_factory, formset_factory

from isisdata.models import *
from isisdata.utils import strip_punctuation
from isisdata import operations
from isisdata.filters import *
from isisdata import tasks as data_tasks


from curation.tracking import TrackingWorkflow
from zotero.models import ImportAccession

from curation.forms import *

from curation.contrib.views import check_rules
from curation import tasks as curation_tasks

import iso8601, rules, datetime
from itertools import chain
from unidecode import unidecode


def _get_datestring_for_authority(authority):
    return ', '.join([attribute.value.display for attribute in authority.attributes.all()])


def _get_datestring_for_citation(citation):
    if citation.publication_date:
        return citation.publication_date.isoformat()[:4]
    return 'missing'


def _get_citation_title(citation):
    title = citation.title
    if not title:
        for relation in citation.ccrelations:
            if relation.type_controlled in [CCRelation.REVIEW_OF, CCRelation.REVIEWED_BY]:
                return u'Review: %s' % relation.subject.title if relation.subject.id != citation.id else relation.object.title
        return u'Untitled review'
    return title


def _get_authors_editors(citation):
    return ', '.join([getattr(relation.authority, 'name', 'missing') + ' ('+  relation.get_type_controlled_display() + ')' for relation in citation.acrelations
                if relation.type_controlled in [ACRelation.AUTHOR, ACRelation.EDITOR]])

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def dashboard(request):
    """
    """
    template = 'curation/dashboard.html'
    context = {}
    return render(request, template, context)



@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def datasets(request):
    """
    """
    template = 'curation/dashboard.html'
    context = {
        'curation_section':'datasets',
    }
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
#@check_rules('can_create_record')
def create_citation(request):

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    }

    template = 'curation/citation_create_view.html'

    if request.method == 'GET':
        form = CitationForm(user=request.user)

        context.update({
            'form': form,
        })
        partdetails_form = PartDetailsForm(request.user)
        context.update({
            'partdetails_form': partdetails_form,
        })
    elif request.method == 'POST':
        form = CitationForm(request.user, request.POST)
        partdetails_form = PartDetailsForm(request.user, citation_id = None, data=request.POST)

        if form.is_valid() and partdetails_form.is_valid():
            form.cleaned_data['public'] = False
            #form.cleaned_data['record_status_value'] = CuratedMixin.INACTIVE why does this not work?
            citation = form.save()
            citation.record_status_value = CuratedMixin.INACTIVE
            citation.save()

            if partdetails_form:
                partdetails_form.save()
            return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)))
        else:
            context.update({
                'form' : form,
                'partdetails_form': partdetails_form,
            })

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
#@check_rules('can_create_record')
def create_authority(request):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    }

    template = 'curation/authority_create_view.html'
    person_form = None
    if request.method == 'GET':
        form = AuthorityForm(user=request.user, prefix='authority')

        context.update({
            'form': form,
        })
    elif request.method == 'POST':
        authority = Authority()
        if request.POST.get('authority-type_controlled', '') == Authority.PERSON:
            authority = Person()
            person_form = PersonForm(request.user, None, request.POST, instance=authority)

        form = AuthorityForm(request.user, request.POST, prefix='authority', instance=authority)
        if form.is_valid() and (person_form is None or person_form.is_valid()):
            if person_form:
                person_form.save()

            form.cleaned_data['public'] = False
            form.cleaned_data['record_status_value'] = CuratedMixin.INACTIVE
            authority = form.save()

            return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority.id,)))
        else:
            context.update({
                'form' : form,
            })
    return render(request, template, context)


# TODO this method needs to be logged down!
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def quick_create_acrelation(request):
    if request.method == 'POST':
        authority_id = request.POST.get('authority_id')
        citation_id = request.POST.get('citation_id')
        type_controlled = request.POST.get('type_controlled')
        type_broad_controlled = request.POST.get('type_broad_controlled')
        instance = ACRelation.objects.create(
            authority_id=authority_id,
            citation_id=citation_id,
            type_controlled=type_controlled,
            type_broad_controlled=type_broad_controlled,
            public=True,
            record_status_value=CuratedMixin.ACTIVE,
        )

        response_data = {
            'acrelation': {
                'id': instance.id,
                'type_controlled': instance.type_controlled,
                'get_type_controlled_display': instance.get_type_controlled_display(),
                'type_broad_controlled': instance.type_broad_controlled,
                'authority': {
                    'id': instance.authority.id,
                    'name': instance.authority.name,
                    'type_controlled': instance.authority.type_controlled,
                },
                'citation': {
                    'id': instance.citation.id,
                    'name': _get_citation_title(instance.citation),
                    'type_controlled': instance.citation.type_controlled,
                },
            }
        }
        return JsonResponse(response_data)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def create_ccrelation_for_citation(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
    }
    if request.method == 'GET':
        ccrelation = CCRelation()
        initial={}
        if citation.type_controlled == Citation.CHAPTER:
            ccrelation.object = citation
            ccrelation.type_controlled = CCRelation.INCLUDES_CHAPTER
            initial['type_controlled'] = CCRelation.INCLUDES_CHAPTER
            initial['object'] = citation.id
        else:
            initial['subject'] = citation.id
            ccrelation.subject = citation
        form = CCRelationForm(prefix='ccrelation', initial=initial, instance=ccrelation)
        context.update({
            'ccrelation': ccrelation,
        })

    elif request.method == 'POST':
        form = CCRelationForm(request.POST, prefix='ccrelation')
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=ccrelations')

    context.update({
        'form': form,
    })
    template = 'curation/citation_ccrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def ccrelation_for_citation(request, citation_id, ccrelation_id=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    ccrelation = None if not ccrelation_id else get_object_or_404(CCRelation, pk=ccrelation_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'ccrelation': ccrelation,
    }
    if request.method == 'GET':
        if ccrelation:
            form = CCRelationForm(instance=ccrelation, prefix='ccrelation')
        else:
            form = CCRelationForm(prefix='ccrelation', initial={'subject': citation.id})

    elif request.method == 'POST':
        form = CCRelationForm(request.POST, instance=ccrelation, prefix='ccrelation')
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=ccrelations')

    context.update({
        'form': form,
    })
    template = 'curation/citation_ccrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def create_acrelation_for_authority(request, authority_id):
    authority = get_object_or_404(Authority, pk=authority_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,

    }
    if request.method == 'GET':
        initial = {
            'authority': authority.id,
            'name_for_display_in_citation': authority.name
        }
        type_controlled = request.GET.get('type_controlled', None)
        if type_controlled:
            initial.update({'type_controlled': type_controlled.upper()})
        form = ACRelationForm(prefix='acrelation', initial=initial)

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, prefix='acrelation')
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority.id,)) + '?tab=acrelations')

    context.update({
        'form': form,
    })
    template = 'curation/authority_acrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def acrelation_for_authority(request, authority_id, acrelation_id):
    authority = get_object_or_404(Authority, pk=authority_id)
    acrelation = get_object_or_404(ACRelation, pk=acrelation_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'acrelation': acrelation,
    }
    if request.method == 'GET':
        form = ACRelationForm(instance=acrelation, prefix='acrelation')

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, instance=acrelation, prefix='acrelation')
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority.id,)) + '?tab=acrelations')

    context.update({
        'form': form,
    })
    template = 'curation/authority_acrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def create_acrelation_for_citation(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
    }
    if request.method == 'GET':
        initial = {
            'citation': citation.id,
        }
        type_controlled = request.GET.get('type_controlled', None)
        if type_controlled:
            initial.update({'type_controlled': type_controlled.upper()})
        form = ACRelationForm(prefix='acrelation', initial=initial)

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, prefix='acrelation')
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=acrelations')

    context.update({
        'form': form,
    })
    template = 'curation/citation_acrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def acrelation_for_citation(request, citation_id, acrelation_id=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    acrelation = None if not acrelation_id else get_object_or_404(ACRelation, pk=acrelation_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'acrelation': acrelation,
    }
    if request.method == 'GET':
        form = ACRelationForm(instance=acrelation, prefix='acrelation')

    elif request.method == 'POST':
        form = ACRelationForm(request.POST, instance=acrelation, prefix='acrelation')
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=acrelations')

    context.update({
        'form': form,
    })
    template = 'curation/citation_acrelation_changeview.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def tracking_for_citation(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
    }

    trackType = request.GET.get('type', None)
    workflow = TrackingWorkflow(citation)
    if workflow.is_workflow_action_allowed(trackType):
        tracking = Tracking()
        tracking.type_controlled = trackType
        tracking.modified_by = request.user
        date = datetime.datetime.now()
        tracking.tracking_info = date.strftime("%Y/%m/%d") + " {} {}".format(request.user.first_name, request.user.last_name)
        tracking.citation = citation
        tracking.save()
        citation.tracking_state = trackType
        citation.save()
    return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation_id,)) + '?tab=tracking')


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def tracking_for_authority(request, authority_id):
    authority = get_object_or_404(Authority, pk=authority_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
    }

    template = 'curation/authority_tracking_create.html'

    if request.method == "POST":
        form = AuthorityTrackingForm(request.POST, instance=AuthorityTracking(), prefix='tracking')
        if form.is_valid():
            tracking = form.save(commit=False)
            tracking.authority = authority
            tracking.save()
            authority.tracking_state = tracking.type_controlled
            authority.save()
            return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority_id,)) + '?tab=tracking')
    else:
        # just always shows tracking form if not post
        form = AuthorityTrackingForm(prefix='tracking', initial={'subject': authority_id})


    context.update({
        'form': form,
    })

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_attribute_for_citation(request, citation_id, attribute_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    attribute = get_object_or_404(Attribute, pk=attribute_id)
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'attribute': attribute,
    }
    if request.GET.get('confirm', False):
        attribute.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=attributes')
    template = 'curation/citation_attribute_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_linkeddata_for_citation(request, citation_id, linkeddata_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'linkeddata': linkeddata,
    }

    if request.GET.get('confirm', False):
        linkeddata.delete()

        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=linkeddata')
    template = 'curation/citation_linkeddata_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_linkeddata_for_authority(request, authority_id, linkeddata_id, format=None):
    authority = get_object_or_404(Authority, pk=authority_id)
    linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'linkeddata': linkeddata,
    }

    if request.GET.get('confirm', False):
        linkeddata.delete()

        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority.id,)) + '?tab=linkeddata')
    template = 'curation/authority_linkeddata_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_language_for_citation(request, citation_id):
    # TODO: format?
    citation = get_object_or_404(Citation, pk=citation_id)
    language_id = request.GET.get('language', None)
    if not language_id:
        raise Http404

    citation.language.remove(language_id)
    citation.save()
    return JsonResponse({'result': True})


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def add_language_for_citation(request, citation_id):
    # TODO: format?
    citation = get_object_or_404(Citation, pk=citation_id)
    language_id = request.POST.get('language', None)
    if not language_id:
        raise Http404

    language = get_object_or_404(Language, pk=language_id)
    citation.language.add(language)
    citation.save()
    result = {
        'language': {
            'id': language_id,
            'name':language.name
        }
    }
    return JsonResponse(result)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_ccrelation_for_citation(request, citation_id, ccrelation_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    ccrelation = get_object_or_404(CCRelation, pk=ccrelation_id)
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'ccrelation': ccrelation,
    }
    if request.GET.get('confirm', False):
        ccrelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=ccrelations')
    template = 'curation/citation_ccrelation_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def delete_acrelation_for_citation(request, citation_id, acrelation_id, format=None):
    citation = get_object_or_404(Citation, pk=citation_id)
    acrelation = get_object_or_404(ACRelation, pk=acrelation_id)
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'acrelation': acrelation,
    }
    if request.GET.get('confirm', False):
        acrelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=acrelations')
    template = 'curation/citation_acrelation_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_acrelation_for_authority(request, authority_id, acrelation_id, format=None):
    authority = get_object_or_404(Authority, pk=authority_id)
    acrelation = get_object_or_404(ACRelation, pk=acrelation_id)
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'acrelation': acrelation,
    }
    if request.GET.get('confirm', False):
        acrelation.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority.id,)) + '?tab=acrelations')
    template = 'curation/authority_acrelation_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def delete_attribute_for_authority(request, authority_id, attribute_id, format=None):
    authority = get_object_or_404(Authority, pk=authority_id)
    attribute = get_object_or_404(Attribute, pk=attribute_id)
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'attribute': attribute,
    }
    if request.GET.get('confirm', False):
        attribute.delete()
        if format == 'json':
            return JsonResponse({'result': True})
        return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority.id,)) + '?tab=attributes')
    template = 'curation/authority_attribute_delete.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def linkeddata_for_citation(request, citation_id, linkeddata_id=None):

    template = 'curation/citation_linkeddata_changeview.html'
    citation = get_object_or_404(Citation, pk=citation_id)
    linkeddata = None

    if linkeddata_id:
        linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'linkeddata': linkeddata,
    }

    if request.method == 'GET':
        if linkeddata:
            linkeddata_form = LinkedDataForm(instance=linkeddata,
                                             prefix='linkeddata')
        else:
            initial = {}
            type_controlled = request.GET.get('type_controlled', None)
            if type_controlled:
                q = {'name__istartswith': type_controlled}
                qs = LinkedDataType.objects.filter(**q)
                if qs.count() > 0:
                    initial.update({'type_controlled': qs.first()})

            linkeddata_form = LinkedDataForm(prefix='linkeddata',
                                             initial=initial)
    elif request.method == 'POST':
        if linkeddata:    # Update.
            linkeddata_form = LinkedDataForm(request.POST, instance=linkeddata, prefix='linkeddata')
        else:    # Create.
            linkeddata_form = LinkedDataForm(request.POST, prefix='linkeddata')

        if linkeddata_form.is_valid():
            linkeddata_form.instance.subject = citation
            linkeddata_form.save()

            return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=linkeddata')
        else:
            pass
    else:
        redirect('curation:curate_citation', citation_id)

    context.update({
        'linkeddata_form': linkeddata_form,
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def linkeddata_for_authority(request, authority_id, linkeddata_id=None):

    template = 'curation/authority_linkeddata_changeview.html'
    authority = get_object_or_404(Authority, pk=authority_id)
    linkeddata = None

    if linkeddata_id:
        linkeddata = get_object_or_404(LinkedData, pk=linkeddata_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': authority,
        'linkeddata': linkeddata,
    }

    if request.method == 'GET':
        if linkeddata:
            linkeddata_form = LinkedDataForm(instance=linkeddata, prefix='linkeddata')
        else:
            linkeddata_form = LinkedDataForm(prefix='linkeddata')
    elif request.method == 'POST':
        if linkeddata:    # Update.
            linkeddata_form = LinkedDataForm(request.POST, instance=linkeddata, prefix='linkeddata')
        else:    # Create.
            linkeddata_form = LinkedDataForm(request.POST, prefix='linkeddata')

        if linkeddata_form.is_valid():
            linkeddata_form.instance.subject = authority
            linkeddata_form.save()

            return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority.id,)) + '?tab=linkeddata')
        else:
            pass
    else:
        redirect('curation:curate_authority', authority_id)

    context.update({
        'linkeddata_form': linkeddata_form,
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def attribute_for_citation(request, citation_id, attribute_id=None):

    template = 'curation/citation_attribute_changeview.html'
    citation = get_object_or_404(Citation, pk=citation_id)
    attribute, value, value_form, value_form_class = None, None, None, None

    value_forms = {}
    for at in AttributeType.objects.all():
        value_class = at.value_content_type.model_class()
        if value_class is ISODateValue:
            value_forms[at.id] = ISODateValueForm
        else:
            value_forms[at.id] = modelform_factory(value_class,
                                    exclude=('attribute', 'child_class'))

    if attribute_id:
        attribute = get_object_or_404(Attribute, pk=attribute_id)
        if hasattr(attribute, 'value'):
            value = attribute.value.get_child_class()
            value_form_class = value_forms[attribute.type_controlled.id]

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
        'attribute': attribute,
        'value': value,
    }

    if request.method == 'GET':
        if attribute:
            attribute_form = AttributeForm(instance=attribute, prefix='attribute')
            if value:
                value_form = value_form_class(instance=value, prefix='value')
        else:
            attribute_form = AttributeForm(prefix='attribute')


    elif request.method == 'POST':
        if attribute:    # Update.
            attribute_form = AttributeForm(request.POST, instance=attribute, prefix='attribute')

            value_instance = value if value else None
            value_form = value_form_class(request.POST, instance=value_instance, prefix='value')
        else:    # Create.
            attribute_form = AttributeForm(request.POST, prefix='attribute')
            selected_type_controlled = request.POST.get('attribute-type_controlled', None)
            if selected_type_controlled:
                value_form_class = value_forms[int(selected_type_controlled)]
                value_form = value_form_class(request.POST, prefix='value')

        if attribute_form.is_valid() and value_form and value_form.is_valid():

            attribute_form.instance.source = citation
            attribute_form.save()
            value_form.instance.attribute = attribute_form.instance
            value_form.save()

            return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)) + '?tab=attributes')
        else:
            pass

    context.update({
        'attribute_form': attribute_form,
        'value_form': value_form,
        'value_forms': [(i, f(prefix='value')) for i, f in value_forms.iteritems()],
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def attribute_for_authority(request, authority_id, attribute_id=None):

    template = 'curation/authority_attribute_changeview.html'
    authority = get_object_or_404(Authority, pk=authority_id)
    attribute, value, value_form, value_form_class = None, None, None, None

    value_forms = {}
    for at in AttributeType.objects.all():
        value_class = at.value_content_type.model_class()
        if value_class is ISODateValue:
            value_forms[at.id] = ISODateValueForm
        else:
            value_forms[at.id] = modelform_factory(value_class,
                                    exclude=('attribute', 'child_class'))

    if attribute_id:
        attribute = get_object_or_404(Attribute, pk=attribute_id)
        if hasattr(attribute, 'value'):
            value = attribute.value.get_child_class()
            value_form_class = value_forms[attribute.type_controlled.id]

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
        'instance': authority,
        'attribute': attribute,
        'value': value,
    }

    if request.method == 'GET':
        if attribute:
            attribute_form = AttributeForm(instance=attribute, prefix='attribute')
            if value:
                value_form = value_form_class(instance=value, prefix='value')
        else:
            attribute_form = AttributeForm(prefix='attribute')


    elif request.method == 'POST':

        if attribute:    # Update.
            attribute_form = AttributeForm(request.POST, instance=attribute, prefix='attribute')

            value_instance = value if value else None
            value_form = value_form_class(request.POST, instance=value_instance, prefix='value')
        else:    # Create.
            attribute_form = AttributeForm(request.POST, prefix='attribute')
            selected_type_controlled = request.POST.get('attribute-type_controlled', None)
            if selected_type_controlled:
                value_form_class = value_forms[int(selected_type_controlled)]
                value_form = value_form_class(request.POST, prefix='value')

        if attribute_form.is_valid() and value_form and value_form.is_valid():
            attribute_form.instance.source = authority
            attribute_form.save()
            value_form.instance.attribute = attribute_form.instance
            value_form.save()

            return HttpResponseRedirect(reverse('curation:curate_authority', args=(authority.id,)) + '?tab=attributes')
        else:
            pass

    context.update({
        'attribute_form': attribute_form,
        'value_form': value_form,
        'value_forms': [(i, f(prefix='value')) for i, f in value_forms.iteritems()],
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def citation(request, citation_id):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
    }

    citation = get_object_or_404(Citation, pk=citation_id)
    _build_result_set_links(request, context, citation)


    # We use a different template for each citation type.
    if citation.type_controlled == Citation.BOOK:
        template = 'curation/citation_change_view_book.html'
    elif citation.type_controlled in (Citation.REVIEW, Citation.ESSAY_REVIEW):
        template = 'curation/citation_change_view_review.html'
    elif citation.type_controlled == Citation.CHAPTER:
        template = 'curation/citation_change_view_chapter.html'
    elif citation.type_controlled == Citation.ARTICLE:
        template = 'curation/citation_change_view_article.html'
    elif citation.type_controlled == Citation.THESIS:
        template = 'curation/citation_change_view_thesis.html'
    else:
        template = 'curation/citation_change_view.html'

    partdetails_form = None
    context.update({'tab': request.GET.get('tab', None)})
    if request.method == 'GET':
        form = CitationForm(user=request.user, instance=citation)
        tracking_entries = citation.tracking_records.all() #Tracking.objects.filter(subject_instance_id=citation_id)

        tracking_workflow = TrackingWorkflow(citation)
        context.update({
            'form': form,
            'instance': citation,
            'tracking_entries': tracking_entries,
            'can_create_fully_entered': tracking_workflow.is_workflow_action_allowed(Tracking.FULLY_ENTERED),
            'can_create_proofed': tracking_workflow.is_workflow_action_allowed(Tracking.PROOFED),
            'can_create_authorize': tracking_workflow.is_workflow_action_allowed(Tracking.AUTHORIZED),
        })

        # Most (but not all) citation types should have a PartDetails entry.
        if citation.type_controlled in [Citation.ARTICLE, Citation.BOOK,
                                        Citation.REVIEW, Citation.CHAPTER,
                                        Citation.THESIS, Citation.ESSAY_REVIEW]:
            part_details = getattr(citation, 'part_details', None)
            if not part_details:
                part_details = PartDetails.objects.create()
                citation.part_details = part_details
                citation.save()

            partdetails_form = PartDetailsForm(request.user, citation_id,
                                               instance=part_details,
                                               prefix='partdetails')
            context.update({
                'partdetails_form': partdetails_form,
            })
    elif request.method == 'POST':
        form = CitationForm(request.user, request.POST, instance=citation)
        if citation.type_controlled in [Citation.ARTICLE, Citation.BOOK, Citation.REVIEW, Citation.CHAPTER, Citation.THESIS] and hasattr(citation, 'part_details'):
            partdetails_form = PartDetailsForm(request.user, citation_id, request.POST, prefix='partdetails', instance=citation.part_details)
        if form.is_valid() and (partdetails_form is None or partdetails_form.is_valid()):
            form.save()
            if partdetails_form:
                partdetails_form.save()

            forward_type = request.POST.get('forward_type', None)
            if forward_type == "list":
                return HttpResponseRedirect(reverse('curation:citation_list') + "?page=" + str(page))
            elif forward_type == "next":
                next = context.get('next', citation)
                return HttpResponseRedirect(reverse('curation:curate_citation', args=(next.id,)))
            elif forward_type == "previous":
                prev = context.get('previous', citation)
                return HttpResponseRedirect(reverse('curation:curate_citation', args=(prev.id,)))

            return HttpResponseRedirect(reverse('curation:curate_citation', args=(citation.id,)))

        context.update({
            'form': form,
            'instance': citation,
            'partdetails_form': partdetails_form,
        })

    return render(request, template, context)


# TODO: needs documentation.
def _build_next_and_prev(context, current_obj, objects_page, paginator, page,
                         cache_prev_index_key, cache_page_key,
                         cache_request_param_key, session):
    if objects_page:
        user_session = session
        request_params = user_session.get(cache_request_param_key, {})

        result_list = list(objects_page.object_list)
        prev_index = user_session.get(cache_prev_index_key, None)
        index = None

        if current_obj in result_list:
            index = result_list.index(current_obj)

            # this is a fix for the duplicate results issue
            # is this more stable than having a running index for the record
            # looked at? I don't know, but this works, so I say it's stable enough!
            index = _get_corrected_index(prev_index, index)

        # if current citation is not on current page (page turns)
        # check if it's on next page
        if index == None and paginator.num_pages > page:
            objects_page = paginator.page(page+1)
            result_list = list(objects_page.object_list)
            # update current page number
            if current_obj in result_list:
                index = result_list.index(current_obj)

                # this is a fix for the duplicate results issue
                # is this more stable than having a running index for the record
                # looked at? I don't know, but this work, so I say it's stable enough!
                index = _get_corrected_index(prev_index, index)
                if index != None:
                    page = page+1
                    user_session[cache_page_key] = page
                    request_params['page'] = page

                    user_session[cache_request_param_key] = request_params

        # check if it's on previous page
        if index == None and page > 1:
            objects_page = paginator.page(page-1)
            result_list = list(objects_page.object_list)
            # update current page number
            if current_obj in result_list:
                page = page-1
                index = result_list.index(current_obj)
                user_session[cache_page_key] = page

                # update back to list link
                request_params['page'] = page

                user_session[cache_request_param_key] = request_params

        # let's get next and previous if we have an index
        if index != None:
            # store current index for duplication issue
            user_session[cache_prev_index_key] = index

            next = result_list[index+1] if len(result_list) > index+1 else None
            # if next is not on this page, get the next one
            if not next:
                # if there are more pages
                # take the first element from the next page
                if paginator.num_pages > page:
                    objects_page = paginator.page(page+1)
                    next_page = list(objects_page.object_list)
                    if len(next_page) > 0:
                        next = next_page[0]

            previous = result_list[index-1] if index > 0 else None
            # if previous is on previous page
            if not previous:
                # if we're not on the first page
                if page > 1:
                    objects_page = paginator.page(page-1)
                    prev_page = list(objects_page.object_list)
                    if len(prev_page) > 0:
                        previous = prev_page[len(prev_page)-1]

            context.update({
                'next': next,
                'previous': previous,
                'index': paginator.page(page).start_index() + index,
            })


def _get_corrected_index(prev_index, index):
    # this is a fix for the duplicate results issue
    # is this more stable than having a running index for the record
    # looked at? I don't know, but this work, so I say it's stable enough!
    if prev_index == index:
        return index

    if prev_index != None:
        if ((index == 0 and prev_index != 1 and prev_index != 39) or
          (index == 39 and  prev_index != 0 and prev_index != 38) or
          (index != 0 and index != 39 and index != prev_index + 1 and index != prev_index -1)):
            return None
    return index


def _build_result_set_links(request, context, citation):
    """
    This function build all the info that the previous/next/back to list links from  a given
    request object, context object for the page, and the citation that should be displayed.
    After calling this method, the context object will have five additional properties:
    * next: the next citation in the result set
    * previous: the previous citation in the result set
    * index: the current position in the result set
    * request_params: request parameters that went into the function call
    * total: the total number of found citations
    """
    user_session = request.session
    page = user_session.get('citation_page', 1)
    get_request = user_session.get('citation_filters', None)
    if get_request and 'o' in get_request and isinstance(get_request['o'], list):
        if len(get_request['o']) > 0:
            get_request['o'] = get_request['o'][0]
        else:
            get_request['o'] = "publication_date"
    queryset = operations.filter_queryset(request.user, Citation.objects.all())

    filtered_objects = CitationFilter(get_request, queryset=queryset)
    paginator = Paginator(filtered_objects.qs, 40)

    citations_page = paginator.page(page)

    _build_next_and_prev(context, citation, citations_page, paginator, page, 'citation_prev_index', 'citation_page', 'citation_request_params', user_session)

    request_params = user_session.get('citation_request_params', "")
    context.update({
        'request_params': request_params,
        'total': filtered_objects.qs.count(),
    })


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Citation, 'citation_id'))
def subjects_and_categories(request, citation_id):
    citation = get_object_or_404(Citation, pk=citation_id)

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'instance': citation,
    }

    _build_result_set_links(request, context, citation)

    template = 'curation/citation_subjects_categories.html'

    return render(request, template, context)

# Deleted class QueryDictWraper; we're not using it. -E


def _citations_get_filter_params(request):
    """
    Build ``filter_params`` for GET request in citation list view.
    """
    all_params = {}
    additional_params_names = ["page", "zotero_accession", "in_collections"]
    user_session = request.session
    filter_params = user_session.get('citation_filters', {})
    if 'o' in filter_params and isinstance(filter_params['o'], list):
        if len(filter_params['o']) > 0:
            filter_params['o'] = filter_params['o'][0]
        else:
            filter_params['o'] = "publication_date"

    if not 'o' in filter_params.keys():
        filter_params['o'] = 'publication_date'

    for key in additional_params_names:
        all_params[key] = request.GET.get(key, '')

    # Let the GET parameter override the cached POST parameter, in case the
    #  curator is originating in the collections view.
    if "in_collections" in all_params:
        filter_params["in_collections"] = all_params["in_collections"]
    return filter_params, all_params


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def citations(request):
    template = 'curation/citation_list_view.html'

    user_session = request.session
    if request.method == 'POST':
        # We need to be able to amend the filter parameters, so we create a new
        #  mutable QueryDict from the POST payload.
        raw_params = request.POST.urlencode().encode('utf-8')
        filter_params = QueryDict(raw_params, mutable=True)
        all_params = {}
    elif request.method == 'GET':
        filter_params, all_params = _citations_get_filter_params(request)

    # Default sort order. TODO: move this to the CitationFilterSet itself.
    if 'o' not in filter_params or not filter_params['o']:
        filter_params['o'] = 'title_for_sort'

    # We use the filter parameters in this form to specify the queryset for
    #  bulk actions.
    if isinstance(filter_params, QueryDict):
        encoded_params = filter_params.urlencode().encode('utf-8')
    else:
        _params = QueryDict(mutable=True)
        for k, v in filter(lambda (k, v): v is not None, filter_params.items()):
            _params[k] = v
        encoded_params = _params.urlencode().encode('utf-8')

    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'citations',
        'filter_params': encoded_params,
    }

    queryset = operations.filter_queryset(request.user, Citation.objects.all())
    fields = ('record_status_value', 'id', 'type_controlled', 'public', 'publication_date')
    filtered_objects = CitationFilter(filter_params, queryset=queryset.select_related('part_details'))

    # filters_active = len(filter(lambda (k, v): v and k != 'page', filter_params.items())) > 0

    if filtered_objects.form.is_valid():
        request_params = filtered_objects.form.cleaned_data
        all_params.update(request_params)

        currentPage = all_params.get('page', 1)
        if not currentPage:
            currentPage = 1

        user_session['citation_request_params'] = all_params
        user_session['citation_filters'] = request_params
        user_session['citation_page'] = int(currentPage)
        user_session['citation_prev_index'] = None

    context.update({
        'objects': filtered_objects,
        # 'filters_active': filters_active,
        'result_count': filtered_objects.qs.count()
    })
    print 'start render'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def authorities(request):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    }

    additional_params_names = ["page"]
    all_params = {}

    user_session = request.session

    if request.method == 'POST':
        filter_params = QueryDict(request.POST.urlencode().encode('utf-8'),
                                  mutable=True)
    elif request.method == 'GET':
        filter_params = user_session.get('authority_filters', {})
        if not 'o' in filter_params.keys():
            filter_params['o'] = 'name_for_sort'
        for key in additional_params_names:
            all_params[key] = request.GET.get(key, '')
    if 'o' not in filter_params:
        filter_params['o'] = 'name_for_sort'
    elif isinstance(filter_params['o'], list):
        if len(filter_params['o']) > 0:
            filter_params['o'] = filter_params['o'][0]
        else:
            filter_params['o'] = 'name_for_sort'



    #user_session['authority_request_params'] = request.META['QUERY_STRING']
    #user_session['authority_get_request'] = request.GET
    currentPage = request.GET.get('page', 1)
    #user_session['authority_page'] = int(currentPage)
    #user_session['authority_prev_index'] = None

    template = 'curation/authority_list_view.html'
    queryset = operations.filter_queryset(request.user, Authority.objects.all())
    filtered_objects = AuthorityFilter(filter_params, queryset=queryset)

    filters_active = filter_params
    filters_active = filters_active or len([v for k, v in request.GET.iteritems() if len(v) > 0 and k != 'page']) > 0

    if filtered_objects.form.is_valid():
        request_params = filtered_objects.form.cleaned_data
        for key in request_params:
            all_params[key] = request_params[key]

        currentPage = all_params.get('page', 1)
        if not currentPage:
            currentPage = 1

        user_session['authority_request_params'] = all_params
        user_session['authority_filters'] = request_params
        user_session['authority_page'] = int(currentPage)
        user_session['authority_prev_index'] = None

    context.update({
        'objects': filtered_objects,
        'filters_active': filters_active
    })

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_access_view_edit', fn=objectgetter(Authority, 'authority_id'))
def authority(request, authority_id):
    context = {
        'curation_section': 'datasets',
        'curation_subsection': 'authorities',
    }

    context.update({'tab': request.GET.get('tab', None)})
    authority = get_object_or_404(Authority, pk=authority_id)
    template = 'curation/authority_change_view.html'
    person_form = None
    if request.method == 'GET':

        user_session = request.session
        page = user_session.get('authority_page', 1)
        get_request = user_session.get('authority_filters', None)

        # Something odd going on with the sorting field (``o``).
        if 'o' in get_request and isinstance(get_request['o'], list):
            if len(get_request['o']) > 0:
                get_request['o'] = get_request['o'][0]
            else:
                get_request['o'] = "name_for_sort"


        queryset = operations.filter_queryset(request.user, Authority.objects.all())
        filtered_objects = AuthorityFilter(get_request, queryset=queryset)
        paginator = Paginator(filtered_objects.qs, 40)
        authority_page = paginator.page(page)

        # ok, let's start the whole pagination/next/previous dance :op
        _build_next_and_prev(context, authority, authority_page, paginator,
                             page, 'authority_prev_index', 'authority_page',
                             'authority_request_params', user_session)

        request_params = user_session.get('authority_request_params', "")

        if authority.type_controlled == Authority.PERSON and hasattr(Authority, 'person'):
            person_form = PersonForm(request.user, authority_id, instance=authority.person)

        form = AuthorityForm(request.user, instance=authority, prefix='authority')

        tracking_entries = authority.tracking_records.all() #Tracking.objects.filter(subject_instance_id=authority_id)

        context.update({
            'request_params': request_params,
            'form': form,
            'instance': authority,
            'person_form': person_form,
            'tracking_entries': tracking_entries,
            'total': filtered_objects.qs.count(),
        })


    elif request.method == 'POST':
        if authority.type_controlled == Authority.PERSON and hasattr(Authority, 'person'):
            person_form = PersonForm(request.user, authority_id, request.POST, instance=authority.person)

        form = AuthorityForm(request.user, request.POST, instance=authority, prefix='authority')
        if form.is_valid() and (person_form is None or person_form.is_valid()):
            if person_form:
                person_form.save()

            form.save()

            return HttpResponseRedirect(reverse('curation:curate_authority', args=[authority.id,]))

        context.update({
            'form': form,
            'person_form': person_form,
            'instance': authority,
            # 'partdetails_form': partdetails_form,
        })

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def quick_and_dirty_language_search(request):
    q = request.GET.get('q', None)
    if not q or len(q) < 3:    # TODO: this should be configurable in the GET.
        return JsonResponse({'results': []})
    queryset = Language.objects.filter(name__istartswith=q)
    results = [{
        'id': language.id,
        'name': language.name,
        'public': True,
    } for language in queryset[:20]]
    return JsonResponse({'results': results})


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def quick_and_dirty_authority_search(request):
    # Ordering: First, sort by closeness of match as follows: exact match; whole word
    # match; partial word match from beginning of word. Second, sort by number of
    # linked items. * * Names without double-hyphens go first * If there are names
    # with double-hyphens and the next character is numeric, sort in descending
    # numerical order * If there are names with double-hyphens and the next character
    # is alpha, sort in ascending alphabetical order

    q = request.GET.get('q', None)
    show_inactive = request.GET.get('show_inactive', 'true') == 'true'

    # In some cases, the curator wants to limit to active only for certain
    #  authority types.
    limit_active_types = request.GET.get('active_types', None)
    type_controlled = request.GET.get('type', None)
    exclude = request.GET.get('exclude', None)

    # In some cases, the curator wants to apply the system parameter only to
    #  specific authority types.
    limit_clasification_types = request.GET.get('system_types', None)
    classification_system = request.GET.get('system', None)

    system_blank = request.GET.get('system_blank', True)
    N = int(request.GET.get('max', 10))
    if not q or len(q) < 3:     # TODO: this should be configurable in the GET.
        return JsonResponse({'results': []})

    query = Q()
    if type_controlled:
        type_array = map(lambda t: t.upper(), type_controlled.split(","))
        query &= Q(type_controlled__in=type_array)

    if limit_active_types:
        type_array = map(lambda t: t.upper(), limit_active_types.split(","))
        query &= ~(Q(type_controlled__in=type_array) & Q(record_status_value=CuratedMixin.INACTIVE))

    if exclude:     # exclude certain types
        exclude_array = map(lambda t: t.upper(), exclude.split(","))
        query &= ~Q(type_controlled__in=exclude_array)

    if classification_system:   # filter by classification system
        system_array = map(lambda t: t.upper(), classification_system.split(","))
        if limit_clasification_types:
            type_array = map(lambda t: t.upper(), limit_clasification_types.split(","))
            q_part = Q(type_controlled__in=type_array) & ~Q(classification_system__in=system_array)
            if system_blank:
                q_part &= ~Q(classification_system__isnull=True)
            query &= ~q_part
        else:
            q_part = Q(classification_system__in=system_array)
            if system_blank:
                q_part = q_part | Q(classification_system__isnull=True)
            query &= q_part

    if not show_inactive:   # Don't show inactive records.
        query &= Q(record_status_value=CuratedMixin.ACTIVE)

    queryset = Authority.objects.filter(query)
    queryset_sw = Authority.objects.filter(query)       # Starts with...
    queryset_exact = Authority.objects.filter(query)    # Exact match.
    queryset_with_numbers = Authority.objects.filter(query)    # partial matches, in chunks; with punctuation and numbers.

    query_parts = re.sub(ur'[0-9]+', u' ', strip_punctuation(q)).split()
    for part in query_parts:
        queryset = queryset.filter(Q(name__icontains=part) | Q(name_for_sort__icontains=unidecode(part)))

    query_parts_numbers = strip_punctuation(q).split()
    for part in query_parts_numbers:
        queryset_with_numbers = queryset_with_numbers.filter(name__icontains=part)

    queryset_sw = queryset_sw.filter(name_for_sort__istartswith=q)
    queryset_exact = queryset_exact.filter(Q(name_for_sort__iexact=q) | Q(name__iexact=q))
    results = []
    result_ids = []

    def _is_int(val):
        try:
            int(val)
            return True
        except:
            return False

    def custom_cmp(a, b):
        if '--' in a.name and '--' in b.name:
            a_remainder = a.name.split('--')[1].strip()
            b_remainder = b.name.split('--')[1].strip()

            # If there are names with double-hyphens and the next character is
            #  numeric, sort in descending numerical order
            if _is_int(a_remainder[0]) and _is_int(b_remainder[0]):
                _v = int(b_remainder[0]) - int(a_remainder[0])
                if _v == 0:
                    if _is_int(a_remainder[0:2]) and _is_int(b_remainder[0:2]):
                        return int(b_remainder[0:2]) - int(a_remainder[0:2])
                    elif _is_int(a_remainder[0:2]):
                        return -1
                    elif _is_int(b_remainder[0:2]):
                        return 1
                    else:
                        return 0
                else:
                    return _v
            # Numeric fragments should go first (e.g. 21st century).
            elif _is_int(a_remainder[0]):
                return -1
            elif _is_int(b_remainder[0]):
                return 1
            else:
                # If there are names with double-hyphens and the next
                #  character is alpha, sort in ascending alphabetical
                #  order.
                return cmp(a_remainder, b_remainder)

        # Names without double-hyphens go first.
        elif '--' in a.name:
            return 1
        elif '--' in b.name:
            return -1
        else:
            return a.acrelation_set.count() - b.acrelation_set.count()

    # first exact matches then starts with matches and last contains matches
    for i, obj in enumerate(chain(sorted(queryset_exact, cmp=custom_cmp),
                                  sorted(queryset_sw, cmp=custom_cmp),
                                  sorted(queryset_with_numbers, cmp=custom_cmp), #.order_by('name'),
                                  sorted(queryset, cmp=custom_cmp))):    # .order_by('name')
        # there are duplicates since everything that starts with a term
        # also contains the term.
        if obj.id in result_ids:
            # make sure we still return 10 results although we're skipping one
            N += 1
            continue
        if i == N:
            break

        result_ids.append(obj.id)
        results.append({
            'id': obj.id,
            'type': obj.get_type_controlled_display(),
            'type_code': obj.type_controlled,
            'name': obj.name,
            'description': obj.description,
            'related_citations': map(lambda s: s.title(), set(obj.acrelation_set.values_list('citation__title_for_sort', flat=True)[:10])),
            'citation_count': obj.acrelation_set.count(),
            'datestring': _get_datestring_for_authority(obj),
            'url': reverse("curation:curate_authority", args=(obj.id,)),
            'public': obj.public,
            'type_controlled': obj.get_type_controlled_display()
        })
    return JsonResponse({'results': results})


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def dataset(request, dataset_id=None):
    return HttpResponse('')


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def search_collections(request):
    q = request.GET.get('query', None)
    queryset = CitationCollection.objects.filter(name__icontains=q)
    results = [{
        'id': col.id,
        'label': col.name,
    } for col in queryset[:20]]
    return JsonResponse(results, safe=False)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def search_zotero_accessions(request):
    q = request.GET.get('query', None)
    queryset = ImportAccession.objects.filter(name__icontains=q)
    results = [{
        'id': accession.id,
        'label': accession.name,
        'date': accession.imported_on
    } for accession in queryset[:20]]
    return JsonResponse(results, safe=False)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def search_datasets(request):
    q = request.GET.get('query', None)
    queryset = Dataset.objects.filter(name__icontains=q)
    results = [{
        'id': ds.id,
        'label': ds.name,
    } for ds in queryset[:20]]
    return JsonResponse(results, safe=False)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_view_user_module')
def users(request, user_id=None):
    from curation.filters import UserFilter
    context = {
        'curation_section': 'users',
    }
    template = 'curation/users.html'
    users =  User.objects.all()
    filterset = UserFilter(request.GET, queryset=users)
    context.update({
        'objects': filterset.qs,
        'filterset': filterset,
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_view_user_module')
def user(request, user_id):
    selected_user = get_object_or_404(User, pk=user_id)


    context = {
        'curation_section': 'users',
        'selected_user': selected_user,
    }
    template = 'curation/user.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_role(request, user_id=None):
    context = {
        'curation_section': 'users',
    }

    if request.method == 'GET':
        template = 'curation/add_role.html'
        form = RoleForm()
        context.update({
            'form': form,
        })
    elif request.method == 'POST':
        form = RoleForm(request.POST)

        if form.is_valid():
            role = form.save()

            return redirect('curation:roles')
        else:
            template = 'curation/add_role.html'
            context.update({
                'form': form,
            })
    else:
        return redirect('curation:roles')

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def remove_role(request, user_id, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        role.users.remove(user)

    return redirect('curation:user', user_id=user.pk)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def delete_role(request, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    if request.method == 'POST':
        if role.users.all():
            usernames = [user.username for user in role.users.all()]
            message = "Only roles that are not assigned to any user can be deleted. This role has the following users assigned: " + ", ".join(usernames) + "."
            messages.add_message(request, messages.ERROR, message)
        else:
            role.delete()

    return redirect('curation:roles')


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_view_user_module')
def role(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    template = 'curation/role.html'
    context = {
        'curation_section': 'users',
        'role': role,
    }

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_view_user_module')
def roles(request):
    roles = IsisCBRole.objects.all()

    template = 'curation/roles.html'
    context = {
        'curation_section': 'users',
        'roles': roles,
    }

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_dataset_rule(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'GET':
        template = 'curation/add_rule.html'
        form = DatasetRuleForm(initial = { 'role': role })
        header_template = get_template('curation/rule_dataset_header.html').render(context)
        context.update({
            'form': form,
            'header': header_template
        })
    elif request.method == 'POST':
        form = DatasetRuleForm(request.POST)

        if form.is_valid():
            rule = form.save()
            rule.role = role
            rule.save()

            return redirect('curation:role', role_id=role.pk)
        else:
            template = 'curation/add_rule.html'
            header_template = get_template('curation/rule_dataset_header.html').render(context)

            context.update({
                'form': form,
                'header': header_template,
            })

        return redirect('curation:role', role_id=role.pk)

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_crud_rule(request, role_id, user_id=None):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'GET':
        template = 'curation/add_rule.html'
        header_template = get_template('curation/rule_crud_header.html').render(context)

        form = CRUDRuleForm(initial = { 'role': role })
        context.update({
            'form': form,
            'header': header_template,
        })
    elif request.method == 'POST':
        form = CRUDRuleForm(request.POST)

        if form.is_valid():
            rule = form.save()
            rule.role = role
            rule.save()

            return redirect('curation:role', role_id=role.pk)
        else:
            template = 'curation/add_rule.html'
            header_template = get_template('curation/rule_crud_header.html').render(context)

            context.update({
                'form': form,
                'header_template': header_template,
            })

        return redirect('curation:role', role_id=role.pk)

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_field_rule(request, role_id, user_id=None, object_type=AccessRule.CITATION):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'GET':
        template = 'curation/add_rule.html'
        if object_type == AccessRule.CITATION:
            form = FieldRuleCitationForm(initial = { 'role': role, 'object_type': object_type})
            header_template = 'curation/rule_field_citation_header.html'
        else:
            form = FieldRuleAuthorityForm(initial = { 'role': role, 'object_type': object_type})
            header_template = 'curation/rule_field_authority_header.html'

        header_template = get_template(header_template).render(context)
        context.update({
            'form': form,
            'header': header_template
        })
    elif request.method == 'POST':
        if object_type == AccessRule.CITATION:
            form = FieldRuleCitationForm(request.POST)
            header_template = 'curation/rule_field_citation_header.html'
        else:
            form = FieldRuleAuthorityForm(request.POST)
            header_template = 'curation/rule_field_authority_header.html'

        if form.is_valid():
            rule = form.save()
            rule.object_type = object_type
            rule.role = role
            rule.save()

            return redirect('curation:role', role_id=role.pk)
        else:
            template = 'curation/add_rule.html'
            header_template = get_template(header_template).render(context)

            context.update({
                'form': form,
                'header': header_template,
            })

        return redirect('curation:role', role_id=role.pk)

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_user_module_rule(request, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'GET':
        template = 'curation/add_rule.html'
        form = UserModuleRuleForm()

        header_template = get_template('curation/rule_user_module_header.html').render(context)
        context.update({
            'form': form,
            'header': header_template
        })
    elif request.method == 'POST':
        form = UserModuleRuleForm(request.POST)

        if form.is_valid():
            rule = form.save()
            rule.role = role
            rule.save()

            return redirect('curation:role', role_id=role.pk)
        else:
            template = 'curation/add_rule.html'
            header_template = get_template('curation/rule_user_module_header.html').render(context)

            context.update({
                'form': form,
                'header_template': header_template,
            })

        return redirect('curation:role', role_id=role.pk)

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def add_role_to_user(request, user_edit_id, user_id=None):
    user = get_object_or_404(User, pk=user_edit_id)

    context = {
        'curation_section': 'users',
    }

    if request.method == 'GET':
        template = 'curation/add_role_to_user.html'
        form = AddRoleForm(initial = { 'users': user })
        context.update({
            'form': form,
        })
    elif request.method == 'POST':
        form = AddRoleForm(request.POST)

        if form.is_valid():
            role_id = form.cleaned_data['role']
            role = get_object_or_404(IsisCBRole, pk=role_id)
            role.users.add(user)
            role.save()

            if request.GET.get('from_user', False):
                return redirect('curation:user', user.pk)

            return redirect('curation:user_list')

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def remove_rule(request, role_id, rule_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)
    rule = get_object_or_404(AccessRule, pk=rule_id)

    if request.method == 'POST':
        rule.delete()

    return redirect('curation:role', role_id=role.pk)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def quick_and_dirty_citation_search(request):
    q = request.GET.get('q', None)
    N = int(request.GET.get('max', 20))
    if not q or len(q) < 3:
        return JsonResponse({'results': []})

    queryset = Citation.objects.all()
    queryset_exact = Citation.objects.all()
    queryset_sw = Citation.objects.all()

    queryset_exact = queryset_exact.filter(title_for_sort=q)
    queryset_sw = queryset_sw.filter(title_for_sort__istartswith=q)

    for part in q.split():
        queryset = queryset.filter(title_for_sort__icontains=part)

    queryset = queryset.order_by('title_for_sort')
    queryset_exact = queryset_exact.order_by('title_for_sort')
    queryset_sw = queryset_sw.order_by('title_for_sort')

    result_ids = []
    results = []
    for i, obj in enumerate(chain(queryset_exact, queryset_sw, queryset)):
        # there are duplicates since everything that starts with a term
        # also contains the term.
        if obj.id in result_ids:
            # make sure we still return 10 results although we're skipping one
            N += 1
            continue
        if i == N:
            break

        result_ids.append(obj.id)
        results.append({
            'id': obj.id,
            'type': obj.get_type_controlled_display(),
            'type_id':obj.type_controlled,
            'title': _get_citation_title(obj),
            'authors': _get_authors_editors(obj),
            'datestring': _get_datestring_for_citation(obj),
            'description': obj.description,
            'url': reverse("curation:curate_citation", args=(obj.id,)),
            'public':obj.public,
        })

    return JsonResponse({'results': results})


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
@check_rules('can_update_user_module')
def change_is_staff(request, user_id):

    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)

        is_staff = request.POST.get('is_staff', False)
        if is_staff == 'True':
            user.is_staff = True
        else:
            user.is_staff = False
        user.save()

    return redirect('curation:user', user_id=user_id)


@check_rules('is_user_superuser')
def change_is_superuser(request, user_id):

    if request.method == "POST":
        user = get_object_or_404(User, pk=user_id)

        is_superuser = request.POST.get('is_superuser', False)
        if is_superuser == 'True':
            user.is_superuser = True
            user.save()

        elif is_superuser == 'False':
            superusers = User.objects.filter(is_superuser=True)

            if len(superusers) > 1:
                user.is_superuser = False
                user.save()
            else:
                message = "This is the only admin user in the system. There have to be at least two adminstrators to remove administrator permissions from a user. "
                messages.add_message(request, messages.ERROR, message)

    return redirect('curation:user', user_id=user_id)


@check_rules('can_update_user_module')
def add_zotero_rule(request, role_id):
    role = get_object_or_404(IsisCBRole, pk=role_id)

    context = {
        'curation_section': 'users',
        'role': role,
    }

    if request.method == 'POST':
        rule = ZoteroRule.objects.create(role_id=role_id)

    return redirect('curation:role', role_id=role.pk)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_select_citation(request):
    template = 'curation/bulk_select_citation.html'
    context = {}
    return render(request, template, context)


def _get_filtered_queryset(request):
    pks = request.POST.getlist('queryset')

    filter_params_raw = request.POST.get('filters')
    filter_params = QueryDict(filter_params_raw, mutable=True)
    pks = request.POST.getlist('queryset')
    if pks:
        filter_params['id'] = ','.join(pks)
    filter_params_raw = filter_params.urlencode().encode('utf-8')

    _qs = operations.filter_queryset(request.user, Citation.objects.all())
    queryset = CitationFilter(filter_params, queryset=_qs)
    return queryset, filter_params_raw


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_action(request):
    """
    User has selected some number of records.

    Selection can be explicit via a list of pks in the ``queryset`` form field,
    or implicit via the ``filters`` from the list view.
    """
    template = 'curation/bulkaction.html'
    form_class = bulk_action_form_factory()
    context = {}

    if request.method != 'POST':
        return HttpResponseRedirect(reverse('curation:citation_list'))

    queryset, filter_params_raw = _get_filtered_queryset(request)

    context.update({'queryset': queryset.qs, 'filters': filter_params_raw})

    if request.GET.get('confirmed', False):
        # Perform the selected action.
        form = form_class(request.POST)
        form.fields['filters'].initial = filter_params_raw
        if form.is_valid():
            tasks = form.apply(request.user, filter_params_raw)
            # task_id = form.apply(queryset.qs, request.user)[0]
            return HttpResponseRedirect(reverse('curation:citation-bulk-action-status') + '?' + '&'.join([urlencode({'task': task}) for task in tasks]))
    else:
        # Prompt to select an action that will be applied to those records.
        form = form_class()
        form.fields['filters'].initial = filter_params_raw

        # form.fields['queryset'].initial = queryset.values_list('id', flat=True)
    context.update({
        'form': form,
    })
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def create_citation_collection(request):
    template = 'curation/citation_collection_create.html'
    context = {}
    if request.method == 'POST':
        queryset, filter_params_raw = _get_filtered_queryset(request)
        if isinstance(queryset, CitationFilter):
            queryset = queryset.qs
        if request.GET.get('confirmed', False):
            form = CitationCollectionForm(request.POST)
            form.fields['filters'].initial = filter_params_raw
            if form.is_valid():
                instance = form.save(commit=False)
                instance.createdBy = request.user
                instance.save()


                instance.citations.add(*queryset)

                # TODO: add filter paramter to select collection.
                return HttpResponseRedirect(reverse('curation:citation_list') + '?in_collections=%i' % instance.id)
        else:
            form = CitationCollectionForm()
            form.fields['filters'].initial = filter_params_raw

        context.update({
            'form': form,
            'queryset': queryset,
        })

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def add_citation_collection(request):
    template = 'curation/citation_collection_add.html'
    context = {}

    if request.method == 'POST':
        queryset, filter_params_raw = _get_filtered_queryset(request)
        if isinstance(queryset, CitationFilter):
            queryset = queryset.qs
        if request.GET.get('confirmed', False):
            form = SelectCitationCollectionForm(request.POST)
            form.fields['filters'].initial = filter_params_raw
            if form.is_valid():
                collection = form.cleaned_data['collection']
                collection.citations.add(*queryset)

                # TODO: add filter paramter to select collection.
                return HttpResponseRedirect(reverse('curation:citation_list') + '?in_collections=%i' % collection.id)
        else:
            form = SelectCitationCollectionForm()
            form.fields['filters'].initial = filter_params_raw

        context.update({
            'form': form,
            'queryset': queryset,
        })

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_action_status(request):
    template = 'curation/citations_bulk_status.html'
    context = {}
    task_ids = request.GET.getlist('task')
    tasks = map(lambda _pk: AsyncTask.objects.get(pk=_pk), task_ids)

    context.update({'tasks': tasks})
    return render(request, template, context)


# TODO: refactor around asynchronous tasks.
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def export_citations_status(request):
    template = 'curation/citations_export_status.html'
    context = {}
    # target = request.GET.get('target')
    task_id = request.GET.get('task_id')
    task = AsyncTask.objects.get(pk=task_id)
    target = task.value

    download_target = 'https://%s.s3.amazonaws.com/%s' % (settings.AWS_EXPORT_BUCKET_NAME, target)
    context.update({'download_target': download_target, 'task': task})
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def export_citations(request):
    # TODO: move some of this stuff out to the export module.

    template = 'curation/citations_export.html'
    context = {}
    if request.method != 'POST':
        return HttpResponseRedirect(reverse('curation:citation_list'))

    queryset, filter_params_raw = _get_filtered_queryset(request)

    if request.GET.get('confirmed', False):
        # The user has selected the desired configuration settings.
        form = ExportCitationsForm(request.POST)
        form.fields['filters'].initial = filter_params_raw

        if form.is_valid():
            # Start the export process.
            tag = slugify(form.cleaned_data.get('export_name', 'export'))
            fields = form.cleaned_data.get('fields')

            # TODO: generalize this, so that we are not tied directly to S3.
            _datestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _out_name = '%s--%s.csv' % (_datestamp, tag)
            # _compress = form.cleaned_data.get('compress_output', False)
            s3_path = 's3://%s:%s@%s/%s' % (settings.AWS_ACCESS_KEY_ID,
                                            settings.AWS_SECRET_ACCESS_KEY,
                                            settings.AWS_EXPORT_BUCKET_NAME,
                                            _out_name)
            # if _compress:
            #     s3_path += '.gz'

            # We create the AsyncTask object first, so that we can keep it
            #  updated while the task is running.
            task = AsyncTask.objects.create()
            result = data_tasks.export_to_csv.delay(request.user.id, s3_path,
                                                    fields, filter_params_raw,
                                                    task.id)

            # We can use the AsyncResult's UUID to access this task later, e.g.
            #  to check the return value or task state.
            task.async_uuid = result.id
            task.value = _out_name
            task.save()

            # Send the user to a status view, which will show the export
            #  progress and a link to the finished export.
            target = reverse('curation:export-citations-status') \
                     + '?' + urlencode({'task_id': task.id})
            return HttpResponseRedirect(target)

    else:       # Display the export configuration form.
        form = ExportCitationsForm()
        form.fields['filters'].initial = filter_params_raw

    context.update({
        'form': form,
        'queryset': queryset,
    })

    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def collections(request):
    """
    List :class:`.Collection` instances.
    """
    from curation.filters import CitationCollectionFilter
    collections = CitationCollection.objects.all()

    filtered_objects = CitationCollectionFilter(request.GET, queryset=collections)
    context = {
        'objects': filtered_objects,
    }
    return render(request, 'curation/collection_list.html', context)
