# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license.
# See the NOTICE for more information.

import sys, os
import restkit

CURDIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(CURDIR, '..', '..'))
sys.path.append(os.path.join(CURDIR, '..'))
sys.path.append(os.path.join(CURDIR, '.'))

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinxtogithub']

templates_path = ['_templates']

source_suffix = '.rst'
master_doc = 'index'

project = 'restkit'
copyright = '2008-2013 Benoît Chesneau <benoitc@e-engura.org>'

version = restkit.__version__
release = version


exclude_trees = ['_build']

if on_rtd:
    pygments_style = 'sphinx'
    html_theme = 'default'
else:
    pygments_style = 'fruity'
    html_theme = 'basic'
    html_theme_path = [""]


html_static_path = ['_static']

htmlhelp_basename = 'restkitdoc'

latex_documents = [
  ('index', 'restkit.tex', 'restkit Documentation',
   'Benoît Chesneau', 'manual'),
]
