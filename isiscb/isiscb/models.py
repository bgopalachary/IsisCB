from django.db import models

class Citation(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    """
    In the format CBB000000000 (CBB followed by a number padded with zeros to
    be nine digits).
    """

    title = models.CharField(max_length=255)
    """
    The name to be used to identify the resource. For reviews that traditionally
    have no title, this should be added as something like “[Review of Title
    (Year) by Author]”.
    """

    description = models.TextField()
    """
    Used for additional bibliographic description, such as content summary. For
    abstracts use the ‘Abstract’ field.
    """

    BOOK = 'BO'
    ARTICLE = 'AR'
    CHAPTER = 'CH'
    REVIEW = 'RE'
    ESSAY_REVIEW = 'ES'
    THESIS = 'TH'
    EVENT = 'EV'
    PRESENTATION = 'PR'
    INTERACTIVE = 'IN'
    WEBSITE = 'WE'
    APPLICATION = 'AP'

    TYPE_CHOICES = (
        (BOOK, 'Book'),
        (ARTICLE, 'Article'),
        (CHAPTER, 'Chapter'),
        (REVIEW, 'Review'),
        (ESSAY_REVIEW, 'Essay Review'),
        (THESIS, 'Thesis'),
        (EVENT, 'Event'),
        (PRESENTATION, 'Presentation'),
        (INTERACTIVE, 'Interactive Resource'),
        (WEBSITE, 'Website'),
        (APPLICATION, 'Application'),
    )

    type_controlled = models.CharField(max_length=2, choices=TYPE_CHOICES)
    """
    This list can be extended to the resource types specified by Doublin Core
    Recource Types http://dublincore.org/documents/resource-typelist/
    """

    additional_titles = models.TextField()
    """
    Alternative names used for the resource. Use for translated titles (e.g.
    titles in a language different than a primary language of the work. If the
    work itself is a translation, than the translated title is the ‘Title’). The
    translated work may be linked to the original through a Citation to Citation
    link.
    """

    abstract = models.TextField()
    """
    Use for abstract or detailed summaries of a work.
    """

    edition_details = models.TextField()
    """
    Use for describing the edition or version of the resource. Include names of
    additional contributors if necessary for clarification (such as translators,
    introduction by, etc). Always, use relationship table to list contributors
    (even if they are specified here).
    """

    physical_details = models.CharField()
    """
    For describing the physical description of the resource. Use whatever
    information is appropriate for the type of resource.
    """

    language = models.CharField()
    volume = models.CharField()
    url = models.URLField()



    # associated objects:
    author_editor = models.ManyToManyField(Authority, through='ACRelation')
    publication_date = models.OneToOneField(Attribute)
    publisher = models.ManyToManyField(Authority, through='ACRelation')
    book_series = models.ManyToManyField(Citation, through='CCRelation')
    journal_name = models.ManyToManyField(Authority, through='ACRelation')
    related_citations = models.ManyToManyField(Citation, through='CCRelation')
    reviewed_books = models.ManyToManyField(Citation, through='CCRelation')
    source_book_for_chapter = models.ManyToManyField(Citation, through='CCRelation')
    # what is this?
    full_citation_from_various = models.CharField()
    subject: models.ManyToManyField(Authority, through='ACRelation')
    # what should be the field type for this one:
    date_for_sorting = models.CharField()

    volume_free_text = models.CharField()
    volume_begin = models.IntegerField()
    volume_end = models.IntegerField()
    issue_free_text = models.CharField()
    issue_begin = models.IntegerField()
    issue_end = models.IntegerField()
    pages_free_text = models.CharField()
    page_begin = models.IntegerField()
    page_end = models.IntegerField()

    # Numerical measure of the extent of the resource such as the number of pages or number of words
    # Should this also contain works (E.g. 'pages', 'words')?
    extent_note = models.TextField()
    extent = models.CharField()

    notes_on_provenance = models.TextField()
    bibliography_file_source_data = models.CharField()
    notes_on_content_not_published = models.TextField()
    metadata_old_record = models.TextField()
    status_of_record = models.CharField()

    # what's with these two:
    record_action = models.CharField()
    record_locked = models.CharField()

    #the following fields are in orange in FM db; why? maybe old data?
    place_publisher_free_text = models.TextField()
    book_series_free_text = models.TextField()
    proofing_journal_name = models.CharField()
    proofing_books_reviewed = models.CharField()
    proofing_related_citations = models.CharField()
    proofing_source_book_for_chapter = models.CharField()
    record_id_old = models.CharField()

    # admin fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField()
    modified_on = models.DateTimeField(auto_now=True)
    modified_by = models.CharField()

class Authority(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    name = models.Charfield()
    description = models.TextField()
    type_controlled = models.CharField()
    alternative_names = models.TextField()

    date_range = models.OneToOneField(Attribute)
    # what should be the field type for this one:
    date_for_sorting = models.CharField()

    # controlled, values: SPW, Neu, MW, SHOT
    classification_system = models.CharField()
    classification_code = models.CharField()
    classification_hierarchy = models.CharField()
    provenance = models.TextField()
    notes_on_content = models.TextField()

    # why are the following in orange?
    authority_id_temp = models.CharField()
    authority_id_2_from_thesaurus_id = models.CharField()
    authority_id_no_longer_used = models.CharField()
    redirect_to_no_longer_used = models.CharField()
    authority_id_2_from_journal_id = models.CharField()

    uri = models.URLField()

    personal_name_last = models.CharField()
    personal_name_first = models.CharField()
    personal_name_suffix = models.CharField()
    personal_name_preferred_form = models.CharField()

    # admin fields
    record_status = models.CharField()
    redirect_to = models.CharField()
    record_history = models.CharField()
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField()
    modified_on = models.DateTimeField(auto_now=True)
    modified_by = models.CharField()
    record_locked = models.CharField()

class ACRelation(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    citation = models.ForeignKey(Citation)
    authority = models.ForeignKey(Authority)

    name = models.CharField()
    description = models.TextField()
    # the following two should come from a controlled vocabulary
    type_controlled = models.CharField()
    type_broad_controlled = models.CharField()
    type_free = models.CharField()

    data_source_field = models.CharField()
    data_display_order = models.CharField()
    confidence_measure = models.FloatField(validators = [MinValueValidator(0), MaxValueValidator(1)])
    relationship_weight = models.FloatField(validators = [MinValueValidator(0), MaxValueValidator(2)])

    # why are the following in orange?
    journal_id_old = models.CharField()
    thesaurus_id_old = models.CharField()
    data_work_1 = models.CharField()
    citation_8_digit_id = models.CharField()
    authority_8_digit_id = models.CharField()
    record_id_old = models.CharField()

    name_format_wester_asian_etc = models.CharField()
    name_as_entered = models.CharField()
    name_for_display_in_citation = models.CharField()
    last = models.CharField()
    first = models.CharField()
    suffix = models.CharField()

    classification_code = models.CharField()

    # admin fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField()
    modified_on = models.DateTimeField(auto_now=True)
    modified_by = models.CharField()
    record_locked = models.CharField()

    # AuthorityID of the record that succeeds this
    # record if this record has become Inactive.
    redirect_to = models.CharField()
    # what does this field do?
    record_history = models.CharField()

class CCRelation(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    # todo

class Attribute(models.Model):
    id = models.CharField(max_length=200, primary_key=True)
    # todo
