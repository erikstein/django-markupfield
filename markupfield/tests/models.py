from django.db import models

from markupfield.fields import MarkupField

class Post(models.Model):
    title = models.CharField(max_length=50)
    body = MarkupField('body of post')

    def __unicode__(self):
        return self.title

class Article(models.Model):
    normal_field = MarkupField()
    default_field = MarkupField(default_markup_type='markdown')
    markdown_field = MarkupField(markup_type='markdown')


from markup import RestructuredtextMarkup
import markdown

CUSTOM_MARKUP_FIELD_TYPES = {
    'markdown': markdown.markdown,
    'ReST': RestructuredtextMarkup,
}

class CustomArticle(models.Model):
    text = MarkupField(markup_choices=CUSTOM_MARKUP_FIELD_TYPES, default_markup_type='ReST')
