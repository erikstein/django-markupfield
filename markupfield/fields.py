import types
from django.conf import settings
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.html import linebreaks, urlize
from django.utils.functional import curry
from django.core.exceptions import ImproperlyConfigured
import widgets

_rendered_field_name = lambda name: '_%s_rendered' % name
_markup_type_field_name = lambda name: '%s_markup_type' % name

# build _DEFAULT_MARKUP_TYPES
_DEFAULT_MARKUP_TYPES = {
    'html': lambda markup: markup,
    'plain': lambda markup: urlize(linebreaks(markup)),
}

try:
    import pygments
    PYGMENTS_INSTALLED = True

    def _register_pygments_rst_directive():
        from docutils import nodes
        from docutils.parsers.rst import directives
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, TextLexer
        from pygments.formatters import HtmlFormatter

        DEFAULT = HtmlFormatter()
        VARIANTS = {
            'linenos': HtmlFormatter(linenos=True)
        }

        def pygments_directive(name, arguments, options, content, lineno,
                               content_offset, block_text, state, state_machine):
            try:
                lexer = get_lexer_by_name(arguments[0])
            except ValueError:
                # no lexer found - use the text one instead of an exception
                lexer = TextLexer()
            formatter = options and VARIANTS[options.keys()[0]] or DEFAULT
            parsed = highlight(u'\n'.join(content), lexer, formatter)
            return [nodes.raw('', parsed, format='html')]
        pygments_directive.arguments = (1, 0, 1)
        pygments_directive.content = 1
        directives.register_directive('code', pygments_directive)

except ImportError:
    PYGMENTS_INSTALLED = False

try:
    import markdown
    _DEFAULT_MARKUP_TYPES['markdown'] = markdown.markdown

    # try and replace if pygments & codehilite are available
    if PYGMENTS_INSTALLED:
        try:
            from markdown.extensions.codehilite import makeExtension
            _DEFAULT_MARKUP_TYPES['markdown'] = curry(markdown.markdown, extensions=['codehilite(css_class=highlight)'])
        except ImportError:
            pass

except ImportError:
    pass

try:
    from docutils.core import publish_parts

    if PYGMENTS_INSTALLED:
        _register_pygments_rst_directive()

    def render_rest(markup):
        overrides = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})
        parts = publish_parts(source=markup, writer_name="html4css1",
                              settings_overrides=overrides)
        return parts["fragment"]

    _DEFAULT_MARKUP_TYPES['restructuredtext'] = render_rest
except ImportError:
    pass

try:
    import textile
    _DEFAULT_MARKUP_TYPES['textile'] = curry(textile.textile,
                                             encoding='utf-8', output='utf-8')
except ImportError:
    pass

_MARKUP_TYPES = getattr(settings, 'MARKUP_FIELD_TYPES', _DEFAULT_MARKUP_TYPES)


class Markup(object):

    def __init__(self, instance, field_name, rendered_field_name,
                 markup_type_field_name):
        # instead of storing actual values store a reference to the instance
        # along with field names, this makes assignment possible
        self.instance = instance
        self.field_name = field_name
        self.rendered_field_name = rendered_field_name
        self.markup_type_field_name = markup_type_field_name

    # raw is read/write
    def _get_raw(self):
        return self.instance.__dict__[self.field_name]

    def _set_raw(self, val):
        setattr(self.instance, self.field_name, val)

    raw = property(_get_raw, _set_raw)

    # markup_type is read/write
    def _get_markup_type(self):
        return self.instance.__dict__[self.markup_type_field_name]

    def _set_markup_type(self, val):
        return setattr(self.instance, self.markup_type_field_name, val)

    markup_type = property(_get_markup_type, _set_markup_type)

    # rendered is a read only property
    def _get_rendered(self):
        return getattr(self.instance, self.rendered_field_name)
    rendered = property(_get_rendered)

    # allows display via templates to work without safe filter
    def __unicode__(self):
        return mark_safe(self.rendered)
    
    def render(self, val):
        raise NotImplementedError
        # Must be implemented by subclasses and return the value for rendered self.raw


class MarkupDescriptor(object):

    def __init__(self, field, markup_choices):
        self.field = field
        self.rendered_field_name = _rendered_field_name(self.field.name)
        self.markup_type_field_name = _markup_type_field_name(self.field.name)
        self.markup_choices = markup_choices

    def __get__(self, instance, owner):
        if instance is None:
            raise AttributeError('Can only be accessed via an instance.')
        markup = instance.__dict__[self.field.name]
        markup_type = instance.__dict__[self.markup_type_field_name]
        if markup_type is None:
            return None
        if type(self.markup_choices[markup_type]) == types.FunctionType:
            # Just a plain filter function, use default Markup class
            if markup is None:
                return None
            markup_class = Markup
        else:
            markup_class = self.markup_choices[markup_type]
        return markup_class(instance, self.field.name, self.rendered_field_name,
                      self.markup_type_field_name)

    def __set__(self, obj, value):
        if isinstance(value, Markup):
            obj.__dict__[self.field.name] = value.raw
            setattr(obj, self.rendered_field_name, value.rendered)
            setattr(obj, self.markup_type_field_name, value.markup_type)
        else:
            obj.__dict__[self.field.name] = value


class MarkupField(models.TextField):

    def __init__(self, verbose_name=None, name=None, markup_type=None,
                 markup_choices=None, default_markup_type=None, **kwargs):
        if markup_type and (markup_choices or default_markup_type):
            raise ValueError('Cannot specify both markup_type and markup_choices/default_markup_type')
        if markup_choices and not default_markup_type:
            raise ValueError('No default_markup_type specified.')
        self.default_markup_type = markup_type or default_markup_type
        self.markup_choices = markup_choices or _MARKUP_TYPES
        if (self.default_markup_type and
            self.default_markup_type not in self.markup_choices):
            raise ValueError('Invalid markup type, allowed values: %s' %
                             ', '.join(self.markup_choices.iterkeys()))
        self.markup_type_editable = markup_type is None
        super(MarkupField, self).__init__(verbose_name, name, **kwargs)

    def contribute_to_class(self, cls, name):
        keys = self.markup_choices.keys()
        markup_type_field = models.CharField(max_length=30,
            choices=zip(keys, keys), default=self.default_markup_type,
            editable=self.markup_type_editable, blank=self.blank)
        rendered_field = models.TextField(editable=False)
        markup_type_field.creation_counter = self.creation_counter+1
        rendered_field.creation_counter = self.creation_counter+2
        cls.add_to_class(_markup_type_field_name(name), markup_type_field)
        cls.add_to_class(_rendered_field_name(name), rendered_field)
        super(MarkupField, self).contribute_to_class(cls, name)
        
        setattr(cls, self.name, MarkupDescriptor(self, self.markup_choices))

    def pre_save(self, model_instance, add):
        value = super(MarkupField, self).pre_save(model_instance, add)
        if value.markup_type not in self.markup_choices:
            raise ValueError('Invalid markup type (%s), allowed values: %s' %
                             (value.markup_type,
                              ', '.join(self.markup_choices.iterkeys())))
        
        if type(self.markup_choices[value.markup_type]) == types.FunctionType:
            rendered = self.markup_choices[value.markup_type](value.raw)
        else:
            rendered = value.render()
        setattr(model_instance, _rendered_field_name(self.attname), rendered)
        return value.raw

    def get_db_prep_value(self, value):
        if isinstance(value, Markup):
            return value.raw
        else:
            return value

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return value.raw

    def formfield(self, **kwargs):
        defaults = {'widget': widgets.MarkupTextarea}
        defaults.update(kwargs)
        return super(MarkupField, self).formfield(**defaults)

# register MarkupField to use the custom widget in the Admin
from django.contrib.admin.options import FORMFIELD_FOR_DBFIELD_DEFAULTS
FORMFIELD_FOR_DBFIELD_DEFAULTS[MarkupField] = {'widget': widgets.AdminMarkupTextareaWidget}
