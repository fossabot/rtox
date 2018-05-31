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
import re
import subprocess

from fabric.api import cd
from fabric.api import env
from fabric.api import hide
from fabric.api import lcd
from fabric.api import local
from fabric.api import run
from fabric.api import shell_env
from fabric.context_managers import settings

from rtox import __version__
from rtox import logging
import rtox.untox as untox_code


class Client(object):
    """An SSH client that can runs remote commands as if they were local."""

    def __init__(self,
                 hostname,
                 port=None,
                 user=getpass.getuser(),
                 passenv=''):
        """Initialize an SSH client based on the given configuration."""
        if user:
            env.user = user
            env.host_string = "%s@%s" % (user, hostname)  # , 22)
        else:
            env.user = getpass.getuser()
            env.host_string = hostname

        env.host_string = hostname
        self.rsync_host_string = hostname  # port need to be separated
        self.full_host_string = "%s@%s" % (user, hostname)

        if port:
            env.host_string += ":%s" % port
            self.full_host_string += ":%s" % port
            self.rsync_params = '-e "ssh -p %s" ' % port
        else:
            self.rsync_params = ''

        if os.path.isfile('.gitignore'):
            # Load excludes from .gitignore
            # See https://stackoverflow.com/a/15373763/99834
            self.rsync_params += \
                '--include .git --exclude-from="$(git ls-files ' \
                '--exclude-standard -oi --directory >.git/ignores.tmp && ' \
                'echo .git/ignores.tmp)" '
        else:
            for exclude in ['.tox', '.pytest_cache', '*.pyc', '__pycache__']:
                self.rsync_params += '--exclude %s ' % exclude

        env.colorize_errors = True
        env.forward_agent = True
        # linewise avoids weird interpolation of stderr and stdout output
        env.linewise = True
        self.passenv = {'RTOX': '1'}
        for k in passenv.split():
            if k in os.environ:
                self.passenv[k] = os.environ[k]
        logging.debug("PASSENV: %s" % self.passenv)

    def run(self, command, silent=False, cwd='', warn_only=False):
        """Run the given command remotely over SSH, echoing output locally."""
        env.warn_only = warn_only
        with settings(shell_env(**self.passenv)), cd(cwd):
            if silent:
                with hide('output', 'warnings'):
                    result = run(command,
                                 shell=True,
                                 pty=False,  # for combine_stderr=False
                                 combine_stderr=False,
                                 shell_escape=False)
            else:
                result = run(command,
                             shell=True,
                             pty=False,  # for combine_stderr=Falsek
                             combine_stderr=False,
                             shell_escape=False)
        return result

    def local(self, command, silent=False, cwd=''):
        """Run the given command locally, echoing output."""
        with lcd(cwd):
            if silent:
                with hide('output', 'warnings'):
                    result = local(command)
            else:
                result = local(command)
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
    config.set('ssh', 'port', '')
    config.set('ssh', 'passenv', '')
    config.set('ssh', 'folder', 'hash')

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

    if config.get('ssh', 'folder') not in ['hash', 'repo']:
        raise SystemExit("Invalid config value found for 'folder', "
                         "possible values: hash, repo.")
    return config


def local_repo():
    output = subprocess.check_output(['git', 'remote', '--verbose']).decode()

    # Parse the output to find the fetch URL.
    return output.split('\n')[0].split(' ')[0].split('\t')[1]


def local_diff():
    return subprocess.check_output(['git', 'diff', 'master'])


def shell_escape(arg):
        return "'%s'" % (arg.replace(r"'", r"'\''"), )


def cli():
    """Run the command line interface of the program."""

    if os.environ.get('RTOX') == '1':
        logging.warn("Avoinding recursive call of rtox, returning 0.")
        raise SystemExit(0)
    parser = \
        argparse.ArgumentParser(
            prog='rtox',
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
    if config.get('ssh', 'folder') == 'hash':
        target_folder = hashlib.sha1(repo.encode('utf-8')).hexdigest()
    else:
        target_folder = re.sub('\.git$', '', repo.rsplit('/', 1)[-1])

    remote_repo_path = '~/.rtox/%s' % target_folder.encode('utf-8')
    remote_untox = '~/.rtox/untox'

    client = Client(
        config.get('ssh', 'hostname'),
        port=config.get('ssh', 'port'),
        user=config.get('ssh', 'user'),
        passenv=config.get('ssh', 'passenv'))

    # Bail immediately if we don't have what we need on the remote host.
    # We prefer to check if python modules are installed instead of the cli
    # scipts because on some platforms (like MacOS) script may not be in PATH.
    for cmd in ['python -m pip install --user tox tox-pyenv virtualenv',
                'python -m virtualenv --version',
                'python -m tox --version']:
        result = client.run(cmd, silent=True)
        if result.failed:
            raise SystemExit(
                'Remote command `%s` returned %s. Output: %s' %
                (result.real_command,
                 result.return_code,
                 result.stderr))

    # Ensure we have a directory to work with on the remote host.
    client.run('mkdir -p %s' % remote_repo_path, silent=True)

    # Clone the repository we're working on to the remote machine.
    rsync_path = '%s:%s' % (
        client.rsync_host_string,
        remote_repo_path.replace('~', '\~'))
    logging.info('Syncing the local repository to %s ...' % rsync_path)
    # Distributing .tox folder would be nonsense and most likely cause
    # breakages.
    client.local('rsync %s--update --delete -a . %s' % (
                 client.rsync_params,
                 rsync_path))

    if os.path.isfile('bindep.txt'):
        if client.run('which bindep', silent=True, warn_only=True).succeeded:
            result = client.run('bindep test', cwd=remote_repo_path)
            if result.failed:
                logging.warn("Failed to run bindep! Result %s" %
                             result.return_code)

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
        command = ['%s; %s; python -m tox' %
                   (remote_untox,
                    "pip install --no-deps -e .")]
    else:
        command = ['python -m tox']
    command.extend(tox_args)

    cmd = ' '.join(command)
    result = client.run(cmd, cwd=remote_repo_path)

    raise SystemExit(result.return_code)


if __name__ == '__main__':
    cli()
