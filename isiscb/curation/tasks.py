"""
"""

from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.http import QueryDict
from isisdata.models import Citation, CRUDRule
from isisdata.filters import CitationFilter
from isisdata.operations import filter_queryset
from django.contrib.auth.models import User


def _load_model_instance(module, cname, pk, qs=False):
    _mod = __import__(module, fromlist=[cname])
    model = getattr(_mod, cname)
    if qs:
        return model.objects.filter(pk=pk)
    return model.objects.get(pk=pk)


@shared_task
def update_instance(*args, **kwargs):
    if len(args) == 5:    # Called directly with intended signature.
        module, cname, pk, field, value = args
    elif len(args) == 6:    # Upstream task may have returned a value.
        _, module, cname, pk, field, value = args
    obj = _load_model_instance(module, cname, pk)
    setattr(obj, field, value)
    obj.save()


@shared_task
def update_task(task, amount):
    task.current_value += amount
    task.save()


@shared_task
def update_task_status(task, status):
    # task.value = value
    task.status = status
    task.save()


@shared_task
def bulk_update_instances(task_data, queryset, field, value):
    """
    Iteratively update objects in a queryset, using the ``save()`` method.

    This is necessary for some cases in which we need to trigger post-save
    signals and execute instance-specific code.
    """
    task_module, task_model, task_pk = task_data
    task = _load_model_instance(task_module, task_model, task_pk)

    for obj in queryset:
        setattr(obj, field, value)
        obj.save()


def _get_filtered_citation_queryset(filter_params_raw, user_id=None):
    """

    Parameters
    ----------
    params : str

    Returns
    -------
    :class:`.QuerySet`
    """

    # We need a mutable QueryDict.
    filter_params = QueryDict(filter_params_raw, mutable=True)

    _qs = Citation.objects.all()
    if user_id:
        _qs = filter_queryset(User.objects.get(pk=user_id), _qs, CRUDRule.UPDATE)
    queryset = CitationFilter(filter_params, queryset=_qs).qs
    return queryset, filter_params_raw


@shared_task
def bulk_change_tracking_state(user_id, filter_params_raw, target_state, info,
                               notes, task_id=None):
    from curation.tracking import TrackingWorkflow
    from isisdata.models import AsyncTask, Tracking
    import math

    queryset, _ = _get_filtered_citation_queryset(filter_params_raw, user_id)
    # We should have already filtered out ineligible citations, but just in
    #  case....
    queryset = queryset.filter(tracking_state__in=TrackingWorkflow.allowed(target_state))

    _tracking_gen = lambda ident: Tracking(citation_id=ident,
                                           tracking_info=info,
                                           notes=notes,
                                           modified_by_id=user_id)

    try:
        queryset.update(tracking_state=target_state)
        Tracking.objects.bulk_create(map(_tracking_gen, queryset.values_list('id', flat=True)))
        if task_id:
            task = Task.objects.get(pk=task_id)
            task.state = 'SUCCESS'
            task.save()
            print 'success:: %s' % str(task_id)
    except Exception as E:
        print 'bulk_change_tracking_state failed for %s:: %s' % (filter_params_raw, target_state),
        print E
        if task_id:
            task = Task.objects.get(pk=task_id)
            task.value = str(E)
            task.state = 'FAILURE'
            task.save()
