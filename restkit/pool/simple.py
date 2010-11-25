# -*- coding: utf-8 -
#
# This file is part of restkit released under the MIT license. 
# See the NOTICE for more information.

import warnings
warnings.warn("The Simplepool module is deprecated.  Please use the "
        "restkit.conn.TConnectionManager class instead.",
        DeprecationWarning, stacklevel=2)



from restkit.conn import TConnectionManager

SimplePool = TConnectionManager
