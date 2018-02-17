# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pbr.version import VersionInfo

_v = VersionInfo('rtox').semantic_version()
__version__ = _v.release_string()
version_info = _v.version_tuple()

__all__ = (
    '__version__',
    'version_info',
)
