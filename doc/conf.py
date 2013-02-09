# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import sys, os
import restkit

sys.path.append(os.getcwd())

DOCS_DIR = os.path.abspath(os.path.dirname(__file__))
# for gunicorn_ext.py
sys.path.append(os.path.join(DOCS_DIR, os.pardir))
# To make sure we get this version of gunicorn
sys.path.insert(0, os.path.join(DOCS_DIR, os.pardir, os.pardir))



extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'epydoc_ext',
        'sphinxtogithub']

templates_path = ['_templates']

source_suffix = '.rst'
master_doc = 'index'

project = u'restkit'
copyright = u'2008-2012 Benoît Chesneau <benoitc@e-engura.org>'


version = restkit.__version__
release = version


exclude_trees = ['_build']
pygments_style = 'fruity'
html_theme = 'basic'
html_theme_path = [""]
html_static_path = ['_static']

htmlhelp_basename = 'restkitdoc'

latex_documents = [
  ('index', 'restkit.tex', u'restkit Documentation',
   u'Benoît Chesneau', 'manual'),
]
