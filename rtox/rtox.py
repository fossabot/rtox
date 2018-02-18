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
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
import getpass
import hashlib
import os.path
import subprocess
import sys
import time

import paramiko


class Client(object):
    """An SSH client that can runs remote commands as if they were local."""

    def __init__(self, hostname, port=None, user=None):
        """Initialize an SSH client based on the given configuration."""
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname, port=port, username=user)

    def run(self, command):
        """Run the given command remotely over SSH, echoing output locally."""
        channel = self.ssh.get_transport().open_session()
        channel.exec_command(command)
        stdin, stdout, stderr = self.ssh.exec_command(command, get_pty=True)

        # Pass remote stdout and stderr to the local terminal
        try:
            while not channel.exit_status_ready():
                if channel.recv_ready():
                    length = len(channel.in_buffer)
                    sys.stdout.write(channel.recv(length))

                if channel.recv_stderr_ready():
                    length = len(channel.in_stderr_buffer)
                    sys.stderr.write(channel.recv_stderr(length))

                time.sleep(0.1)

            if channel.recv_ready():
                length = len(channel.in_buffer)
                sys.stdout.write(channel.recv(length))
            if channel.recv_stderr_ready():
                length = len(channel.in_stderr_buffer)
                sys.stderr.write(channel.recv_stderr(length))

            return channel.recv_exit_status()
        except KeyboardInterrupt:
            channel.close()
            return 1


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
    print("INFO: Loading config from %s" % f)
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
    config = load_config()

    repo = local_repo()
    remote_repo_path = '~/.rtox/%s' % hashlib.sha1(repo).hexdigest()

    client = Client(
        config.get('ssh', 'hostname'),
        port=config.getint('ssh', 'port'),
        user=config.get('ssh', 'user'))

    # Bail immediately if we don't have what we need on the remote host.
    # We prefer to check if python modules are installed instead of the cli
    # scipts because on some platforms (like MacOS) script may not be in PATH.
    cmd = 'output=`python -m virtualenv --version && \
           python -m tox --version` || \
           { echo $output; exit 1; }'
    if client.run(cmd) != 0:
        raise SystemExit(
            'Ensure tox and virtualenv are available on the remote host.')

    # Ensure we have a directory to work with on the remote host.
    client.run('mkdir -p %s' % remote_repo_path)

    # Clone the repository we're working on to the remote machine.
    print('Syncing the local repository to the remote host...')
    subprocess.check_call([
        'rsync',
        '--update',
        '--exclude',
        '.tox',
        '-a',
        '.',
        '%s@%s:%s' % (
            config.get('ssh', 'user'),
            config.get('ssh', 'hostname'),
            remote_repo_path)])

    # removing .tox folder is done
    command = ['cd %s ; PY_COLORS=1 python -m tox' % remote_repo_path]
    command.extend(sys.argv[1:])
    status_code = client.run(' '.join(command))

    raise SystemExit(status_code)


if __name__ == '__main__':
    cli()
