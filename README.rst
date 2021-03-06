[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fpycontribs%2Frtox.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2Fpycontribs%2Frtox?ref=badge_shield)

.. image:: https://travis-ci.org/pycontribs/rtox.svg?branch=master
    :target: https://travis-ci.org/pycontribs/rtox
 
``rtox``
========

This project represents an experimental development workflow with the following
considerations in mind:

- `tox <https://tox.readthedocs.org/en/latest/>`_ is an excellent tool for
  managing test activities in a `virtualenv
  <https://virtualenv.readthedocs.org/en/latest/>`_.

- Servers in the cloud are faster and far more powerful than my local
  development environment (usually a laptop).

- Latency introduced to the command line by a remote connection, especially on
  bad WiFi, is painful.

- Running huge test suites on a cloud server doesn't drain my laptop's battery
  (or spin up my desktop's fans) like running them locally would.

- Your local development platform might not actually have the binary
  dependencies available that your project requires from your target platform
  (developing a Linux application on OS X, for example).

- Running tests with tox is easy. Running tests with ``rtox`` on a remote
  host against the local codebase should be just as easy.

This project currently makes a few assumptions that you'd have to meet for it
to be useful to you:

- You're a Python developer (that's why you're interested in tox, right?).

- You're using ``git``.

- You're working on a publicly available repository (I'd like to break this
  assumption).

Usage
-----

Configure ``rtox`` with an ``.rtox.cfg`` file like the following::

    [ssh]
    user = root
    hostname = localhost
    port = 22

rtox will look for config file in current folder or its parents and use
``~/.rtox.cfg`` as fallback. This allows user to have different configs
for different projects or groups of projects.

``rtox`` simply needs to be pointed at an SSH host with ``git``, ``tox`` and
``virtualenv`` installed.

Once it's configured, just use ``rtox`` in place of ``tox``. For example::

    $ rtox -e py27 -e pep8

The state of your local codebase will be mirrored to the remote host, and tox
will be executed there.

untox
=====

Untox is a small script that obliterates any tox.ini commands that are
installing python packages inside the virtualenv, removing sepctions
like ``deps``, ``pip install ...``, truncating ``requirements.txt`` files
and enabling ``sitepackages = True`` on all tox environments.

Its purpose is to enable testing of python code with only system packages,
something that may be desired by those that are planning to ship these
modules as RPMs, DEBs.

``untox`` script is installed as a command alongside ``rtox`` and once
called it expectes to find a tox.ini in current folder. Be warned that changes
are made in-place without any backup.

You also have the option to call ``rtox --untox ...`` which will run untox
on the remote system after doing the rsync and before running tox. This
option is handy as it keeps the local repository untoched.



## License
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fpycontribs%2Frtox.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2Fpycontribs%2Frtox?ref=badge_large)