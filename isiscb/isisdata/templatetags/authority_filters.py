from __future__ import unicode_literals
from django import template
from isisdata.models import *

register = template.Library()

@register.filter
def is_person(authority):
    return authority.type_controlled == Authority.PERSON

@register.filter
def is_attribute_visible(attribute):
    if type(attribute.value.get_child_class()) == AuthorityValue and attribute.value.get_child_class().value:
        if not attribute.value.get_child_class().value.public:
            return False

    return attribute.public
