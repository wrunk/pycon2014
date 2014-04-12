#!/usr/bin/env python
# Copyright 2013 DeadHeap.com

from __future__ import absolute_import


from jinja2 import Environment, FileSystemLoader
import logging as _log
from nudge.json import ObjDict
from nudge.publisher import ServicePublisher, Endpoint
import nudge.arg as args
import os
import re

_base_path = '/'.join(os.path.dirname(os.path.realpath(__file__)).split('/')[:-1]) + '/'
_log.info(_base_path)


def test():
    return {'test': True}

endpoints = [
    Endpoint(name='Poop', uri='/test', function=test, method='GET')
]


wsgi_app = ServicePublisher(endpoints=endpoints)
