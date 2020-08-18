from __future__ import unicode_literals
from builtins import object
from rest_framework import viewsets, serializers, mixins, permissions

from isisdata.models import Citation, Authority, ACRelation, PartDetails
from zotero.models import *


class InstanceResolutionEventSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = InstanceResolutionEvent
        excude = []


class AuthoritySerializer(serializers.ModelSerializer):
    resolutions = InstanceResolutionEventSerializer(many=True, read_only=True)
    class Meta(object):
        model = Authority
        exclude = ('modified_on_fm',
                   'modified_by_fm',
                   'created_on_fm',
                   'created_by_fm',
                   'redirect_to')
        read_only_fields = ('id',)


class ACRelationSerializer(serializers.ModelSerializer):
    resolutions = InstanceResolutionEventSerializer(many=True, read_only=True)

    class Meta(object):
        model = ACRelation
        exclude = ('modified_on_fm',
                   'modified_by_fm',
                   'created_on_fm',
                   'created_by_fm')
        read_only_fields = ('id',)

    def update(self, instance, validated_data):
        """
        Overwritten to allow related fields.
        """
        for attr, value in list(validated_data.items()):
            if attr == 'authority':
                instance.authority = value
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance


class PartDetailsSerializer(serializers.ModelSerializer):
    class Meta(object):
        model = PartDetails
        exclude = []


class CitationSerializer(serializers.ModelSerializer):
    resolutions = InstanceResolutionEventSerializer(many=True, read_only=True)
    acrelation_set = ACRelationSerializer(many=True, read_only=True)
    part_details = PartDetailsSerializer()

    class Meta(object):
        model = Citation
        exclude = ('modified_on_fm',
                   'modified_by_fm',
                   'created_on_fm',
                   'created_by_fm',
                   'related_citations')

    def update(self, instance, validated_data):
        """
        Overwritten to allow related fields.
        """
        for attr, value in list(validated_data.items()):
            if attr == 'part_details':
                for a, v in list(value.items()):
                    setattr(instance.part_details, attr, value)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance

class DraftAuthoritySerializer(serializers.ModelSerializer):
    resolutions = InstanceResolutionEventSerializer(many=True)
    resolved = serializers.BooleanField()

    class Meta(object):
        model = DraftAuthority
        exclude = []


class DraftACRelationSerializer(serializers.ModelSerializer):
    authority = DraftAuthoritySerializer()

    class Meta(object):
        model = DraftACRelation
        exclude = []


class DraftCitationSerializer(serializers.ModelSerializer):
    authority_relations = DraftACRelationSerializer(many=True)

    class Meta(object):
        model = DraftCitation
        exclude = []
