from django.contrib import admin
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.admin import GenericTabularInline, GenericStackedInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet, generic_inlineformset_factory
from django import forms
from django.forms import widgets, formsets, models
from django.forms.models import BaseModelFormSet, BaseInlineFormSet, inlineformset_factory
from isisdata.models import *
from simple_history.admin import SimpleHistoryAdmin




# TODO: The Choice widget cannot handle this many choices. Consider using an
#  autocomplete, or some other widget that loads ``object`` choices dynamically
#  via AJAX.
class CCRelationForm(forms.ModelForm):
    class Meta:
        model = CCRelation
        fields = ('object', )


class CCRelationInline(admin.TabularInline):
    fk_name = 'subject'
    model = CCRelation
    form = CCRelationForm
    extra = 1


class ValueWidget(widgets.Widget):
    def __init__(self, attrs=None):
        super(ValueWidget, self).__init__(attrs)

        self.widgets = {
            'textvalue': widgets.TextInput(),
            'datetimevalue': widgets.DateTimeInput(),
            'intvalue': widgets.NumberInput(),
            'floatvalue': widgets.NumberInput(),
            'charvalue': widgets.TextInput(),
            'datevalue': widgets.DateInput(),
            'locationvalue': widgets.TextInput(), # TODO: custom location widget
        }

    def render(self, name, value, attrs=None):
        assign = "widgets.{0} = $('{1}')[0];";
        assignments = '\n'.join([assign.format(f,v.render(name, value, attrs))
                                 for f, v in self.widgets.items()])
        if value is None:
            value = ''
        return "<span class='dynamicWidget' value='{0}'>Select an attribute type</span><script>{1}</script>".format(value, assignments)


class ValueField(forms.Field):
    pass


class AttributeInlineForm(forms.ModelForm):
    class Media:
        model = Attribute
        js = ('isisdata/js/jquery-1.11.1.min.js',
              'isisdata/js/widgetmap.js')

    id = forms.CharField(widget=forms.HiddenInput(), required=False)
    value = ValueField(label='Value', widget=ValueWidget())

    def __init__(self, *args, **kwargs):
        # This CSS class allows us to watch for changes in the selected type, so
        #  that we can dynamically change the widget for ``value``.
        css_class = 'attribute_type_controlled'
        self.base_fields['type_controlled'].widget.attrs['class'] = css_class

        super(AttributeInlineForm, self).__init__(*args, **kwargs)

        # Populate value and id fields.
        instance = kwargs.get('instance', None)
        if instance is not None:
            value_initial = instance.value.get_child_class().value
            self.fields['value'].initial = value_initial
            self.fields['id'].initial = instance.id


    def is_valid(self):
        val = super(AttributeInlineForm, self).is_valid()

        if all(x in self.cleaned_data for x in ['value', 'type_controlled']):
            value = self.cleaned_data['value']
            attr_type = self.cleaned_data['type_controlled']
            value_model = attr_type.value_content_type.model_class()
            try:
                value_model.is_valid(value)
            except ValidationError as E:
                self.add_error('value', E)
        return super(AttributeInlineForm, self).is_valid()


class AttributeInlineFormSet(BaseGenericInlineFormSet):
    model = Attribute


class AttributeInline(GenericTabularInline):
    model = Attribute
    form = AttributeInlineForm
    # formset = AttributeInlineFormSet
    formset = generic_inlineformset_factory(Attribute, form=AttributeInlineForm,
                                            formset=AttributeInlineFormSet,
                                            ct_field='source_content_type',
                                            fk_field='source_instance_id')
    extra = 1

    ct_field = 'source_content_type'
    ct_fk_field = 'source_instance_id'

    exclude = ('administrator_notes',
               'record_history',
               'modified_on_fm',
               'modified_by_fm',
               'modified_by',
               'modified_on',
               'created_on_fm',
               'created_by_fm',
               'place',
               'date_iso',
               'id',
               'uri',
               'description')


class AttributeInlineMixin(admin.ModelAdmin):
    inlines = (AttributeInline,)

    def save_formset(self, request, form, formset, change):
        """
        Given an inline formset save it to the database.
        """
        return formset.save()

    def save_related(self, request, form, formsets, change):
        """
        Generate a new ``Value`` instance for each ``Attribute``.
        """
        form.save_m2m()     # Does not include Attributes.

        for formset in formsets:
            instances = self.save_formset(request, form, formset, change=change)
            print 'instances', instances
            # Look only at the Attribute formset.
            if type(formset).__name__ == 'AttributeFormFormSet':
                for attribute, data in zip(instances, formset.cleaned_data):
                    attr_type, value = data['type_controlled'], data['value']
                    value_model = attr_type.value_content_type.model_class()
                    value_instance, created = value_model.objects.get_or_create(
                        attribute=attribute,
                        defaults={
                            'value': value
                        })

                    if not created and value_instance.value != value:
                        value_instance.value = value
                        value_instance.save()


class CitationAdmin(SimpleHistoryAdmin, AttributeInlineMixin):
    list_display = ('id', 'title', 'modified_on_fm', 'modified_by_fm')
    fieldsets = [
        (None, {
            'fields': ('uri',
                       'id',
                       'title',
                       'description',
                       'language',
                       'type_controlled')
        }),
        ('Additional Details', {
            'fields': ('abstract',
                       'edition_details',
                       'physical_details')
        }),
        ('Curation', {
            'fields': ('record_action',
                       'status_of_record',
                       'administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]

    readonly_fields = ('uri', 'modified_on_fm','modified_by_fm')


class AuthorityAdmin(SimpleHistoryAdmin, AttributeInlineMixin):
    list_display = ('id', 'name', 'type_controlled')
    list_filter = ('type_controlled',)

    fieldsets = [
        (None, {
            'fields': ('uri',
                       'id',
                       'name',
                       'description',
                       'type_controlled')
        }),
        ('Classification', {
            'fields': ('classification_system',
                       'classification_code',
                       'classification_hierarchy')
        }),
        ('Curation', {
            'fields': ('record_status',
                       'administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]
    readonly_fields = ('uri',
                       'classification_system',
                       'classification_code',
                       'classification_hierarchy',
                       'modified_on_fm',
                       'modified_by_fm')


class ACRelationAdmin(SimpleHistoryAdmin, AttributeInlineMixin):
    list_display = ('id',
                    'authority',
                    'type_controlled',
                    'citation')

    fieldsets = [
        (None, {
            'fields': ('uri',
                       'citation',
                       'authority',
                       'name',
                       'name_for_display_in_citation',
                       'description')
        }),
        ('Type', {
            'fields': ('type_controlled',
                       'type_broad_controlled',
                       'type_free')
        }),
        ('Curation', {
            'fields': ('administrator_notes',
                       'record_history',
                       'modified_by_fm',
                       'modified_on_fm')
        }),
    ]

    readonly_fields = ('uri',
                       'citation',
                       'authority',
                       'modified_by_fm',
                       'modified_on_fm')


class CCRelationAdmin(SimpleHistoryAdmin, AttributeInlineMixin):
    pass


class AARelationAdmin(SimpleHistoryAdmin, AttributeInlineMixin):
    pass


class LinkedDataAdmin(SimpleHistoryAdmin, AttributeInlineMixin):
    pass


class ValueInline(admin.TabularInline):
    model = Value
    fields = ('cvalue',)
    readonly_fields = ('cvalue', )


class AttributeAdmin(SimpleHistoryAdmin):
    readonly_fields = ('uri', )
    inlines = (ValueInline,)


admin.site.register(Citation, CitationAdmin)
admin.site.register(Authority, AuthorityAdmin)
admin.site.register(ACRelation, ACRelationAdmin)
admin.site.register(CCRelation, CCRelationAdmin)
admin.site.register(AARelation, AARelationAdmin)
admin.site.register(LinkedData, LinkedDataAdmin)
admin.site.register(PartDetails, SimpleHistoryAdmin)
admin.site.register(AttributeType)
# Register your models here.
