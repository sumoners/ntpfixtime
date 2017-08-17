import datetime
import functools
import inspect
import sys
import time
import uuid
import calendar
import unittest
import platform
import warnings
import types
import numbers
import ntplib

from dateutil import parser
from dateutil.tz import tzlocal

real_time = time.time
real_localtime = time.localtime
real_gmtime = time.gmtime
real_strftime = time.strftime
real_date = datetime.date
real_datetime = datetime.datetime

time_offset = None

try:
    real_uuid_generate_time = uuid._uuid_generate_time
except ImportError:
    real_uuid_generate_time = None

try:
    real_uuid_create = uuid._UuidCreate
except ImportError:
    real_uuid_create = None

try:
    import copy_reg as copyreg
except ImportError:
    import copyreg


# Stolen from six
def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

_is_cpython = (
    hasattr(platform, 'python_implementation') and
    platform.python_implementation().lower() == "cpython"
)


class FakeTime(object):
    def __call__(self):
        current_time = datetime.datetime.utcnow()
        return calendar.timegm(current_time.timetuple()) + current_time.microsecond / 1000000.0


class FakeLocalTime(object):
    def __call__(self, t=None):
        if t is not None:
            return real_localtime(t)

        return datetime.datetime.now().timetuple()


class FakeGMTTime(object):
    def __call__(self, t=None):
        if t is not None:
            return real_gmtime(t)
        return datetime.datetime.utcnow().timetuple()


class FakeStrfTime(object):
    def __call__(self, format, time_to_format=None):
        if time_to_format is None:
            time_to_format = FakeLocalTime(time_offset)()
        return real_strftime(format, time_to_format)


class FakeDateMeta(type):
    @classmethod
    def __instancecheck__(self, obj):
        return isinstance(obj, real_date)


def datetime_to_fakedatetime(datetime):
    return FakeDatetime(datetime.year,
                        datetime.month,
                        datetime.day,
                        datetime.hour,
                        datetime.minute,
                        datetime.second,
                        datetime.microsecond,
                        datetime.tzinfo)


def date_to_fakedate(date):
    return FakeDate(date.year,
                    date.month,
                    date.day)


class FakeDate(with_metaclass(FakeDateMeta, real_date)):
    def __new__(cls, *args, **kwargs):
        return real_date.__new__(cls, *args, **kwargs)

    def __add__(self, other):
        result = real_date.__add__(self, other)
        if result is NotImplemented:
            return result
        return date_to_fakedate(result)

    def __sub__(self, other):
        result = real_date.__sub__(self, other)
        if result is NotImplemented:
            return result
        if isinstance(result, real_date):
            return date_to_fakedate(result)
        else:
            return result

    @classmethod
    def today(cls):
        result = real_datetime.now()

        if time_offset:
            result = result + time_offset

        return date_to_fakedate(result)


FakeDate.min = date_to_fakedate(real_date.min)
FakeDate.max = date_to_fakedate(real_date.max)


class FakeDatetimeMeta(FakeDateMeta):
    @classmethod
    def __instancecheck__(self, obj):
        return (obj, real_datetime)


class FakeDatetime(with_metaclass(FakeDatetimeMeta, real_datetime, FakeDate)):
    def __new__(cls, *args, **kwargs):
        return real_datetime.__new__(cls, *args, **kwargs)

    def __add__(self, other):
        result = real_datetime.__add__(self, other)
        if result is NotImplemented:
            return result
        return datetime_to_fakedatetime(result)

    def __sub__(self, other):
        result = real_datetime.__sub__(self, other)
        if result is NotImplemented:
            return result
        if isinstance(result, real_datetime):
            return datetime_to_fakedatetime(result)
        else:
            return result

    def astimezone(self, tz=None):
        return datetime_to_fakedatetime(real_datetime.astimezone(self, tz))

    @classmethod
    def now(cls, tz=None):
        now = real_datetime.now(tz)

        if time_offset:
            now = now + time_offset

        return datetime_to_fakedatetime(now)

    def date(self):
        return date_to_fakedate(self)

    @classmethod
    def today(cls):
        return cls.now(tz=None)

    @classmethod
    def utcnow(cls):
        result = real_datetime.utcnow()

        if time_offset:
            result = real_datetime.utcnow() + time_offset

        return datetime_to_fakedatetime(result)

FakeDatetime.min = datetime_to_fakedatetime(real_datetime.min)
FakeDatetime.max = datetime_to_fakedatetime(real_datetime.max)


def pickle_fake_date(datetime_):
    # A pickle function for FakeDate
    return FakeDate, (
        datetime_.year,
        datetime_.month,
        datetime_.day,
    )


def pickle_fake_datetime(datetime_):
    # A pickle function for FakeDatetime
    return FakeDatetime, (
        datetime_.year,
        datetime_.month,
        datetime_.day,
        datetime_.hour,
        datetime_.minute,
        datetime_.second,
        datetime_.microsecond,
        datetime_.tzinfo,
    )


class _fix_time(object):
    def __init__(self, ntp_server, ignore):
        self.ntp_server = ntp_server
        self.ignore = tuple(ignore)

    def fix(self):
        self.start()

    def start(self):
        if time_offset:
            return time_offset

        c = ntplib.NTPClient()
        globals()['time_offset'] = datetime.timedelta(seconds=c.request(self.ntp_server).offset)

        # Change the modules
        datetime.datetime = FakeDatetime
        datetime.date = FakeDate
        fake_time = FakeTime()
        fake_localtime = FakeLocalTime()
        fake_gmtime = FakeGMTTime()
        fake_strftime = FakeStrfTime()
        time.time = fake_time
        time.localtime = fake_localtime
        time.gmtime = fake_gmtime
        time.strftime = fake_strftime
        uuid._uuid_generate_time = None
        uuid._UuidCreate = None

        copyreg.dispatch_table[real_datetime] = pickle_fake_datetime
        copyreg.dispatch_table[real_date] = pickle_fake_date

        # Change any place where the module had already been imported
        to_patch = [
            ('real_date', real_date, 'FakeDate', FakeDate),
            ('real_datetime', real_datetime, 'FakeDatetime', FakeDatetime),
            ('real_gmtime', real_gmtime, 'FakeGMTTime', fake_gmtime),
            ('real_localtime', real_localtime, 'FakeLocalTime', fake_localtime),
            ('real_strftime', real_strftime, 'FakeStrfTime', fake_strftime),
            ('real_time', real_time, 'FakeTime', fake_time),
        ]
        real_names = tuple(real_name for real_name, real, fake_name, fake in to_patch)
        self.fake_names = tuple(fake_name for real_name, real, fake_name, fake in to_patch)
        self.reals = dict((id(fake), real) for real_name, real, fake_name, fake in to_patch)
        fakes = dict((id(real), fake) for real_name, real, fake_name, fake in to_patch)

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore')

            for mod_name, module in list(sys.modules.items()):
                if mod_name is None or module is None:
                    continue
                elif mod_name.startswith(self.ignore):
                    continue
                elif (not hasattr(module, "__name__") or module.__name__ in ('datetime', 'time')):
                    continue
                for module_attribute in dir(module):
                    if module_attribute in real_names:
                        continue
                    try:
                        attribute_value = getattr(module, module_attribute)
                    except (ImportError, AttributeError, TypeError):
                        # For certain libraries, this can result in ImportError(_winreg) or AttributeError (celery)
                        continue
                    fake = fakes.get(id(attribute_value))
                    if fake:
                        setattr(module, module_attribute, fake)

        datetime.datetime.time_offset = time_offset
        datetime.date.time_offset = time_offset

        return time_offset


def fix_time(ntp_server='br.pool.ntp.org', ignore=None):
    string_type = str

    if ignore is None:
        ignore = []
    ignore.append('six.moves')
    ignore.append('django.utils.six.moves')
    ignore.append('threading')
    ignore.append('Queue')
    ignore.append('ntplib')
    ignore.append('ntpfixtime.ntplib')
    return _fix_time(ntp_server, ignore).fix()


# Setup adapters for sqlite
try:
    import sqlite3
except ImportError:
    # Some systems have trouble with this
    pass
else:
    # These are copied from Python sqlite3.dbapi2
    def adapt_date(val):
        return val.isoformat()

    def adapt_datetime(val):
        return val.isoformat(" ")

    sqlite3.register_adapter(FakeDate, adapt_date)
    sqlite3.register_adapter(FakeDatetime, adapt_datetime)


# Setup converters for pymysql
try:
    import pymysql.converters
except ImportError:
    pass
else:
    pymysql.converters.encoders[FakeDate] = pymysql.converters.encoders[real_date]
    pymysql.converters.conversions[FakeDate] = pymysql.converters.encoders[real_date]
    pymysql.converters.encoders[FakeDatetime] = pymysql.converters.encoders[real_datetime]
    pymysql.converters.conversions[FakeDatetime] = pymysql.converters.encoders[real_datetime]
