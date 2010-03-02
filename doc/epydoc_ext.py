# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import os

from docutils import nodes

def api_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Role `:api:` bridges generated API documentation by epydoc with sphinx.
    
    Add `epydoc_ext` to the list of extensions

    Generate the documentation in build folder::

        $ mkdir -p _build/html/api
        $ epydoc -o _build/html/api ...

    Then run usual sphinx build command.
    """
    
    env = inliner.document.settings.env
    fexists = lambda f: os.path.exists(os.path.join(env.config.api_build, f))
    api_basedir = env.config.api_basedir
    
    modparts = text.split('.')
    name = None
    uri = None
    if fexists(os.path.join(api_basedir, "%s-module.html" % text)):
        uri = "%s/%s" % (api_basedir, "%s-module.html" % text)
        name = '%s' % text
    elif fexists(os.path.join(api_basedir, "%s-class.html" % text)):
        uri =  uri = "%s/%s" % (api_basedir, "%s-class.html" % text)
        name = modparts[-1]
    else:
        method = modparts[-1]
        fprefix = '.'.join(modparts[:-1])
        if fexists(os.path.join(api_basedir, "%s-module.html" % fprefix)):
            name = modparts[-1]
            uri = '%s/%s#%s' % (api_basedir, "%s-module.html" % fprefix,
                            method)
        elif fexists(os.path.join(api_basedir, "%s-class.html" % fprefix)):
            name = '.'.join(modparts[-2:])
            uri = '%s/%s-class.html#%s' % (basedir, fprefix, method)
            
    if not name:
        return [nodes.literal(rawtext, text)], []
    return [nodes.reference(rawtext, name, refuri="%s" % uri, **options)], []


def setup(app):
    app.add_config_value('api_basedir', 'api', '')
    app.add_config_value('api_build', '_build/html/', '')
    app.add_role('api', api_role)
