import django_filters
from django_filters.fields import Lookup
from django_filters.filterset import STRICTNESS
from django.db.models import Q, Count

from zotero.models import *
from isisdata.helper_methods import strip_punctuation
import six
import iso8601

from django_filters import filters

filters.LOOKUP_TYPES = [
    ('', '---------'),
    ('exact', 'Is equal to'),
    ('not_exact', 'Is not equal to'),
    ('lt', 'Lesser than'),
    ('gt', 'Greater than'),
    ('gte', 'Greater than or equal to'),
    ('lte', 'Lesser than or equal to'),
    ('startswith', 'Starts with'),
    ('endswith', 'Ends with'),
    ('icontains', 'Contains'),
    ('not_contains', 'Does not contain'),
]


class ImportAccesionFilter(django_filters.FilterSet):
    strict = STRICTNESS.RAISE_VALIDATION_ERROR
    processed = django_filters.BooleanFilter(name='processed')
    imported_by = django_filters.ModelChoiceFilter(name='imported_by', queryset=User.objects.annotate(num_accessions=Count('importaccession')).filter(num_accessions__gt=0))

    class Meta:
        model = ImportAccession
        fields = ['id', 'name', 'processed', 'imported_on',
                  'imported_by', 'ingest_to']
