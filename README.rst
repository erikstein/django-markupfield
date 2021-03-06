==================
django-markupfield
==================

An implementation of a custom MarkupField for Django.  A MarkupField is in 
essence a TextField with an associated markup type.	 The field also caches
its rendered value on the assumption that disk space is cheaper than CPU 
cycles in a web application.

Installation
============

You can obtain the latest release of django-markupfield via
`PyPI <http://pypi.python.org/pypi/django-markupfield>`_ or check out the 
`latest source <http://github.com/jamesturk/django-markupfield>`_

To install a source distribution::

	python setup.py install

It is also possible to install django-markupfield with
`pip <http://pypi.python.org/pypi/pip>`_ or easy_install.

It is not necessary to add ``'markupfield'`` to your ``INSTALLED_APPS``, it 
merely needs to be on your ``PYTHONPATH``.

Settings
========

To best make use of MarkupField you should define the 
``MARKUP_FIELD_TYPES`` setting, a dictionary of strings to either callables that 
'render' a markup type or subclasses of the ``Markup`` class implementing a 
``render`` method::

	import markdown
	from docutils.core import publish_parts

	def render_rest(markup):
		parts = publish_parts(source=markup, writer_name="html4css1")
		return parts["fragment"]

	MARKUP_FIELD_TYPES = {
		'markdown': markdown.markdown,
		'ReST': render_rest,
	}

Example with a ``Markup`` subclass (Note: If you are using a Markup subclass 
you cannot define MARKUP_FIELD_TYPES in the django settings file)::

	import markdown
	from docutils.core import publish_parts
	from markupfield.fields import Markup
	
	class RestructuredtextMarkup(Markup):
		def render(self):
			parts = publish_parts(source=self.raw, writer_name="html4css1")
			return parts["fragment"]
	
	MARKUP_FIELD_TYPES = {
		'markdown': markdown.markdown,
		'ReST': RestructuredtextMarkup,
	}


If you do not define a ``MARKUP_FIELD_TYPES`` then one is provided with the
following markup types available:

html:
	allows HTML, potentially unsafe
plain:
	plain text markup, calls urlize and replaces text with linebreaks
markdown:
	default `markdown`_ renderer (only if `python-markdown`_ is installed)
restructuredtext:
	default `ReST`_ renderer (only if `docutils`_ is installed)
textile:
	default `textile`_ renderer (only if `textile`_ is installed)

.. _`markdown`: http://daringfireball.net/projects/markdown/
.. _`ReST`: http://docutils.sourceforge.net/rst.html
.. _`textile`: http://hobix.com/textile/quick.html
.. _`python-markdown`: http://www.freewisdom.org/projects/python-markdown/
.. _`docutils`: http://docutils.sourceforge.net/
.. _`python-textile`: http://pypi.python.org/pypi/textile

Usage
=====

Using MarkupField is relatively easy, it can be used in any model definition::

	from django.db import models
	from markupfield.fields import MarkupField

	class Article(models.Model):
		title = models.CharField(max_length=100)
		slug = models.SlugField(max_length=100)
		body = MarkupField()

``Article`` objects can then be created with any markup type defined in 
``MARKUP_FIELD_TYPES``::

	Article.objects.create(title='some article', slug='some-article',
						   body='*fancy*', body_markup_type='markdown')

You will notice that a field named ``body_markup_type`` exists that you did
not declare, MarkupField actually creates two extra fields here 
``body_markup_type`` and ``_body_rendered``.  These fields are always named
according to the name of the declared ``MarkupField``.

Arguments
---------

``MarkupField`` also takes two optional arguments ``default_markup_type`` and
``markup_type``. Either of these arguments may be specified but not both. You
can also pass a list of markup types as defined in ``MARKUP_FIELD_TYPES`` 
together with a ``default_markup_type``.

``default_markup_type``:
	Set a markup_type that the field will default to if one is not specified.
	It is still possible to edit the markup type attribute and it will appear
	by default in ModelForms.

``markup_type``:
	Set markup type that the field will always use, ``editable=False`` is set
	on the hidden field so it is not shown in ModelForms.

``markup_choices``:
	Set a list of possible markup types in the same format as 
	``MARKUP_FIELD_TYPES``. You also must specify a ``default_markup_type``.



Markup subclasses
-----------------

Subclasses of ``Markup`` must implement a ``render``-method, which is used 
by the field to update the ``rendered`` cache on saves::

	import markdown
	from docutils.core import publish_parts
	from markupfield.fields import Markup

	class RestructuredtextMarkup(Markup):
		def render(self):
			parts = publish_parts(source=self.raw, writer_name="html4css1")
			return parts["fragment"]


Accessing a MarkupField on a model
----------------------------------

When accessing an attribute of a model that was declared as a ``MarkupField``
a special ``Markup`` object is returned.  The ``Markup`` object has three
parameters:

``raw``:
	The unrendered markup.
``markup_type``:
	The markup type.
``rendered``:
	The rendered HTML version of ``raw``, this attribute is read-only.

This object has a ``__unicode__`` method that calls 
``django.utils.safestring.mark_safe`` on ``rendered`` allowing MarkupField
objects to appear in templates as their rendered selfs without any template
tag or having to access ``rendered`` directly.

Assuming the ``Article`` model above::

	>>> a = Article.objects.all()[0]
	>>> a.body.raw
	u'*fancy*'
	>>> a.body.markup_type
	u'markdown'
	>>> a.body.rendered
	u'<p><em>fancy</em></p>'
	>>> print unicode(a.body)
	<p><em>fancy</em></p>

Assignment to ``a.body`` is equivalent to assignment to ``a.body.raw`` and
assignment to ``a.body_markup_type`` is equivalent to assignment to 
``a.body.markup_type``.

.. note::
	a.body.rendered is only updated when a.save() is called


Todo
====

 * validate markup_type options
 * convert tests from doctest to unittest
 * add a test for __unicode__

Origin
======

For those coming here via django snippets or the tracker, my original implementation is at https://gist.github.com/67724/3b7497713897fa0021d58e46380e4d80626b6da2

Jacob Kaplan-Moss commented on twitter that he'd possibly like to see a MarkupField in core and I filed a ticket on the Django trac http://code.djangoproject.com/ticket/10317

The resulting django-dev discussion drastically changed the purpose of the field.  While I initially intended to write a version that seemed more acceptable for Django core I wound up feeling that the 'acceptable' version had so little functionality and so much complexity it wasn't worth using.



























































































































































































