# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import sys, os
import restkit

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage']

templates_path = ['_templates']

source_suffix = '.rst'
master_doc = 'index'

project = u'restkit'
copyright = u'2010, Benoît Chesneau <benoitc@e-engura.org>'


version = restkit.__version__
release = version


exclude_trees = ['_build']
pygments_style = 'sphinx'
html_theme = 'basic'
html_theme_path = [""]
html_static_path = ['_static']

htmlhelp_basename = 'restkitdoc'

latex_documents = [
  ('index', 'restkit.tex', u'restkit Documentation',
   u'Benoît Chesneau', 'manual'),
]