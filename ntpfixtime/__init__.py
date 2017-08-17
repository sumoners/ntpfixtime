# -*- coding: utf-8 -*-
"""
ntpfixtime
~~~~~~~~

:copyright: (c) 2017 by Jaison Erick.

"""
from .api import fix_time
from ntplib import NTPException

__title__ = 'ntpfixtime'
__version__ = '0.0.5'
__author__ = 'Jaison Erick'
__license__ = 'MIT'
__copyright__ = 'Copyright 2017 Jaison Erick'


__all__ = ["fix_time", 'NTPException']
