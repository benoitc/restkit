# -*- coding: utf-8 -
# Copyright (c) 2008, Benoît Chesneau <benoitc@e-engura.com>.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cgi
import os


import sys


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))
# setup relative path to simplecouchdb
import unittest
import module_test_runner
# Modules whose tests we will run.

from _server_test import run_server_test

import resource_test
import clients_test


   

def RunAllTests():
    run_server_test()
    test_runner = module_test_runner.ModuleTestRunner()
    test_runner.modules = [resource_test, clients_test]
    test_runner.RunAllTests()

if __name__ == '__main__':
     RunAllTests()
