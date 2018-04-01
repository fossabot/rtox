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
from __future__ import absolute_import
import argparse
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
import getpass
import hashlib
import inspect
import os.path
import subprocess

from fabric.api import env
from fabric.api import hide
from fabric.api import run
from fabric.context_managers import settings

from rtox import __version__
from rtox import logging
import rtox.untox as untox_code


class Client(object):
    """An SSH client that can runs remote commands as if they were local."""

    def __init__(self, hostname, port=None, user=None):
        """Initialize an SSH client based on the given configuration."""
        env.user = user
        if user:
            env.host_string = "%s@%s" % (user, hostname)  # , 22)
        else:
            env.host_string = hostname
        if port:
            env.host_string += ":%s" % port
        env.colorize_errors = True
        env.forward_agent = True
        env.warn_only = True

    def run(self, command, silent=False):
        """Run the given command remotely over SSH, echoing output locally."""
        with settings():
            if silent:
                with hide('output'):
                    result = run(command,
                                 shell=True,
                                 pty=False,  # to assure combine_stderr=False
                                 combine_stderr=False,
                                 shell_escape=False)
            else:
                result = run(command,
                             shell=True,
                             pty=False,  # to assure combine_stderr=Falsek
                             combine_stderr=False,
                             shell_escape=False)
        return result


def load_config():
    """Define and load configuration from a file.

    Configuration is read from ``~/.rtox.cfg``. An example might be::

        [ssh]
        user = root
        hostname = localhost
        port = 22

    SSH passwords are not supported.

    """
    config = configparser.ConfigParser()
    config.add_section('ssh')
    config.set('ssh', 'user', getpass.getuser())
    config.set('ssh', 'hostname', 'localhost')
    config.set('ssh', 'port', '22')

    dir = os.getcwd()
    while dir:
        f = os.path.join(dir, '.rtox.cfg')
        if os.path.isfile(f):
            break
        dir = os.path.dirname(dir)
    if not dir:
        f = os.path.expanduser('~/.rtox.cfg')
    logging.info("Loading config from %s" % f)
    config.read(f)
    return config


def local_repo():
    output = subprocess.check_output(['git', 'remote', '--verbose'])

    # Parse the output to find the fetch URL.
    return output.split('\n')[0].split(' ')[0].split('\t')[1]


def local_diff():
    return subprocess.check_output(['git', 'diff', 'master'])


def shell_escape(arg):
        return "'%s'" % (arg.replace(r"'", r"'\''"), )


def cli():
    """Run the command line interface of the program."""

    parser = \
        argparse.ArgumentParser(
            description='rtox runs tox on a remote machine instead of '
                        'current one.',
            add_help=True)

    parser.add_argument('--version',
                        action='version',
                        version='%%(prog)s %s' % __version__)
    parser.add_argument('--untox',
                        dest='untox',
                        action='store_true',
                        default=False,
                        help='untox obliterates any package installation from \
                              tox.ini files in order to allow testing with \
                              system packages only')
    args, tox_args = parser.parse_known_args()

    config = load_config()

    repo = local_repo()
    remote_repo_path = '~/.rtox/%s' % hashlib.sha1(repo).hexdigest()
    remote_untox = '~/.rtox/untox'

    client = Client(
        config.get('ssh', 'hostname'),
        port=config.getint('ssh', 'port'),
        user=config.get('ssh', 'user'))

    # Bail immediately if we don't have what we need on the remote host.
    # We prefer to check if python modules are installed instead of the cli
    # scipts because on some platforms (like MacOS) script may not be in PATH.
    for cmd in ['python -m virtualenv --version', 'python -m tox --version']:
        result = client.run(cmd, silent=True)
        if result.failed:
            raise SystemExit(
                'Remote command `%s` returned %s. Ourput: %s' %
                result.real_command,
                result.return_code,
                result.stderr)

    # Ensure we have a directory to work with on the remote host.
    client.run('mkdir -p %s' % remote_repo_path)

    # Clone the repository we're working on to the remote machine.
    rsync_path = '%s@%s:%s' % (
        config.get('ssh', 'user'),
        config.get('ssh', 'hostname'),
        remote_repo_path)
    logging.info('Syncing the local repository to %s ...' % rsync_path)
    # Distributing .tox folder would be nonsense and most likely cause
    # breakages.
    subprocess.check_call([
        'rsync',
        '--update',
        '--exclude',
        '.tox',
        '-a',
        '.',
        rsync_path])

    if os.path.isfile('bindep.txt'):
        if client.run('which bindep', silent=True).succeeded:
            cmd = 'cd %s && bindep test' % remote_repo_path
            result = client.run(cmd)
            if result.failed:
                logging.warn("Failed to run bindep! Result %s" %
                             result.status_code)

    if args.untox:
        subprocess.check_call([
            'rsync',
            '--no-R',
            '--no-implied-dirs',
            '--chmod=ugo=rwx',
            '--update',
            '-a',
            inspect.getsourcefile(untox_code),
            '%s@%s:%s' % (
                config.get('ssh', 'user'),
                config.get('ssh', 'hostname'),
                remote_untox)])

    # removing .tox folder is done
    if args.untox:
        command = ['cd %s ; %s; %s; PY_COLORS=1 python -m tox' %
                   (remote_repo_path,
                    remote_untox,
                    "pip install --no-deps -e .")]
    else:
        command = ['cd %s ; PY_COLORS=1 python -m tox' %
                   remote_repo_path]
    command.extend(tox_args)

    cmd = ' '.join(command)
    logging.info("STEP: %s" % cmd)
    status_code = client.run(cmd)

    raise SystemExit(status_code)


if __name__ == '__main__':
    cli()
