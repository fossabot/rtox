# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
from __future__ import unicode_literals
import logging
import os
from pbr.version import VersionInfo

_v = VersionInfo('rtox').semantic_version()
__version__ = _v.release_string()
version_info = _v.version_tuple()

FORMAT = "%(levelname)-8s %(message)s"
verbosity = os.getenv('RTOX_VERBOSITY', '0')
verbosity_map = {
    '0': logging.WARN,
    '1': logging.INFO,
    '2': logging.DEBUG
    }
logging.basicConfig(format=FORMAT, level=verbosity_map[verbosity])

__all__ = (
    '__version__',
    'version_info',
)
