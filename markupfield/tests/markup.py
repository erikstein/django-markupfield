
try:
    import docutils
    from docutils import core
    import docutils.parsers.rst
except ImportError:
    raise ImportError, 'Docutils not found'

from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.html import strip_tags

from markupfield.fields import Markup

INITIAL_HEADER_LEVEL = getattr(settings, "RST_INITIAL_HEADER_LEVEL", 2)
WRITER_NAME = getattr(settings, "RST_WRITER_NAME", 'html') # 'html4css1'
DEFAULT_LANGUAGE_CODE = getattr(settings, "LANGUAGE_CODE", 'en').split("-")[0]


class RestructuredtextMarkup(Markup):
    docutils_settings = {
        'language_code': DEFAULT_LANGUAGE_CODE,
        'doctitle_xform': False, # Don't use first section title as document title
        'input_encoding': 'utf-8',
        'initial_header_level': INITIAL_HEADER_LEVEL,
        'report_level': settings.DEBUG and 1 or 5,
    }
    docutils_settings.update(getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {}))
    
    def render(self, initial_header_level=INITIAL_HEADER_LEVEL, **kwargs):
        """
        Returns the rendered (html).
        """
        settings = self.docutils_settings.copy()
        settings['initial_header_level'] = initial_header_level
        parts = docutils.core.publish_parts(
            source=self.raw, 
            writer_name=WRITER_NAME, 
            settings_overrides=settings
        )
        return parts['fragment']
    render.is_safe = True
    
    def doctree(self, **kwargs):
        """
        Returns the docutils doctree for a given source.
        """
        return docutils.core.publish_doctree(self.raw, settings_overrides=self.docutils_settings)

    def title(self, **kwargs):
        """
        Why don't we use the 'title' part?
        """
        document = self.doctree()
        matches = document.traverse(condition=lambda node: isinstance(node, docutils.nodes.title))
        if len(matches):
            return matches[0].astext()
        else:
            return None
    
    def plaintext(self, **kwargs):
        return self.doctree().astext()
        return strip_tags(self.get_rendered(self.raw, **kwargs))
