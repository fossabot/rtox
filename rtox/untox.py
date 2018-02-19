#!/usr/bin/env python
#
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
#
# Wipes any packet installation code from tox.ini in order to be able
# to run tox commands using system packages.
#
import os
import re


def main():
    f = open('tox.ini', 'r+')
    data = f.read()

    # comments to avoid weird accidents while parsing
    data = re.sub(r'\s*\#.*\n', '', data)

    # consolidate contiuation line breaks
    data = re.sub(r'^(.*)\\\n\s*([^\r\n]+)\n',
                  r'\1\2\n',
                  data,
                  flags=re.MULTILINE)

    # remove install_commands
    data = re.sub(r'\s*install_command.*', '', data)

    # remove pip install commands (including multiline)
    data = re.sub(r'(?m)^\s*pip (.*)?install.*\n?', '', data)

    # remove deps, single and multiline ones
    data = re.sub(r'^\s*deps.*\n(([^\S\n]+[^\n]+\n)+)?',
                  r'',
                  data,
                  flags=re.MULTILINE)

    # replace any existing sitepackages value as True
    data = re.sub(r'\s*sitepackages.*', '\nsitepackages = True', data)

    # adds sitepackages=True to [testenv*] section(s) if needed
    pattern = re.compile(r'^\[testenv[^\]\r\n]+](?:\r?\n(?:[^[\r\n].*)?)*',
                         flags=re.MULTILINE)
    for s in re.findall(pattern, data):
        if 'sitepackages' not in s:
            data = data.replace(s, s + 'sitepackages = True\n')

    f.seek(0)
    f.write(data)
    f.truncate()

    # truncates requirement files just in case they are used in a different way
    for reqs in ['requirements.txt', 'test-requirements.txt']:
        if os.path.isfile(reqs):
            open(reqs, "w").truncate(0)

    # logs changes made as a diff file
    os.system("git diff | tee untox-diff.log")

if __name__ == '__main__':
    main()
