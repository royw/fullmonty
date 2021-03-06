# coding=utf-8

"""
Remote shell with a context over ssh with support for pexpect.

Usage
-----

.. code-block:: python

    with RemoteShell(user=user, password=password, host=host, verbose=True) as remote:
        remote.run("ls ~")
        remote.put(local_file, remote_dir)
        remote.get(remote_file)

"""
import json
import os
import stat
import sys
import re
from time import sleep
from getpass import getpass, getuser

import pexpect
import paramiko
from paramiko import SSHClient

from fullmonty.touch import touch
from fullmonty.simple_logger import debug

try:
    from pexpect.pxssh import pxssh
except ImportError:
    try:
        from pexpect import pxssh
    except ImportError:
        # noinspection PyUnresolvedReferences
        import pxssh

# from pexpect.pxssh import ExceptionPxssh
from scp import SCPClient

try:
    # noinspection PyUnresolvedReferences
    from ordereddict import OrderedDict
except ImportError:
    # noinspection PyUnresolvedReferences
    from collections import OrderedDict

from .ashell import AShell, CR, MOVEMENT

__docformat__ = 'restructuredtext en'
__all__ = ('RemoteShell',)


class RemoteShell(AShell):
    """
    Provides run interface over an ssh connection.

    :param user:
    :type user:
    :param password:
    :type password:
    :param host:
    :type host:
    :param logfile:
    :type logfile:
    :param verbose:
    :type verbose:
    """

    def __init__(self, host, user=None, password=None, logfile=None, verbose=False, password_callback=None):
        super(RemoteShell, self).__init__(is_remote=True, verbose=verbose)
        self.creds_file = os.path.expanduser('~/.remote_shell_rc')
        if host is None or not host:
            raise AttributeError("You must provide a non-empty string for 'host'")
        if user is None:
            user = self.getUser(host)
        if user is None or not user:
            raise AttributeError("You must provide a non-empty string for 'user'")
        if password is None:
            password = self.getPassword(host, user)
        self.user = user
        self.password = password
        self.address = host
        self.port = 22
        # noinspection PyBroadException
        try:
            # noinspection PyCallingNonCallable
            self.ssh = pxssh(timeout=1200)
            self.ssh.login(host, user)
        except:
            if not password:
                password = getpass('password for {user}@{host}: '.format(user=user, host=host))
                if password_callback is not None and callable(password_callback):
                    password_callback(password)
            # noinspection PyCallingNonCallable
            self.ssh = pxssh(timeout=1200)
            self.ssh.login(host, user, password)
        self.accept_defaults = False
        self.logfile = logfile
        self.prefix = None
        self.postfix = None

    def env(self):
        """returns the environment dictionary"""
        environ = {}
        # noinspection PyBroadException
        try:
            for line in self.run('env').split("\n"):
                match = re.match(r'([^=]+)=(.*)', line)
                if match:
                    environ[match.group(1).strip()] = match.group(2).strip()
        except:
            pass
        return environ

    def _report(self, output, out_stream, verbose):
        def _out_string(value):
            if value:
                if isinstance(value, str):
                    self.display(value, out_stream=out_stream, verbose=verbose)
                    output.append(value)

        _out_string(self.ssh.before)
        _out_string(self.ssh.after)

    # noinspection PyUnusedLocal
    def run_pattern_response(self, cmd_args, out_stream=sys.stdout, verbose=True,
                             prefix=None, postfix=None,
                             pattern_response=None, accept_defaults=False,
                             timeout=1200):
        """
        Run the external command and interact with it using the patter_response dictionary
        :param timeout:
        :param accept_defaults:
        :param cmd_args: command line arguments
        :param out_stream: stream verbose messages are written to
        :param verbose: output messages if asserted
        :param prefix: command line arguments prepended to the given cmd_args
        :param postfix: command line arguments appended to the given cmd_args
        :param pattern_response: dictionary whose key is a regular expression pattern that when matched
        results in the value being sent to the running process.  If the value is None, then no response is sent.
        """
        pattern_response_dict = OrderedDict(pattern_response or {})

        if accept_defaults:
            sudo_pattern = 'password for {user}: '.format(user=self.user)
            sudo_response = "{password}\r".format(password=self.password)
            pattern_response_dict[sudo_pattern] = sudo_response
            # accept default prompts, don't match "[sudo] "
            pattern_response_dict[r'\[\S+\](?<!\[sudo\])(?!\S)'] = CR

        pattern_response_dict[MOVEMENT] = None
        pattern_response_dict[pexpect.TIMEOUT] = None

        patterns = list(pattern_response_dict.keys())
        patterns.append(self.ssh.PROMPT)

        args = self.expand_args(cmd_args, prefix=prefix, postfix=postfix)
        command_line = ' '.join(args)
        # info("pattern_response_dict => %s" % repr(pattern_response_dict))
        # self.display("{line}\n".format(line=command_line), out_stream=out_stream, verbose=verbose)

        output = []

        self.ssh.prompt(timeout=0.1)  # clear out any pending prompts
        self._report(output, out_stream=out_stream, verbose=verbose)
        self.ssh.sendline(command_line)
        while True:
            try:
                index = self.ssh.expect(patterns)
                if index == patterns.index(pexpect.TIMEOUT):
                    print("ssh.expect TIMEOUT")
                else:
                    self._report(output, out_stream=out_stream, verbose=verbose)
                    if index == patterns.index(self.ssh.PROMPT):
                        break

                    key = patterns[index]
                    response = pattern_response_dict[key]
                    if response:
                        sleep(0.1)
                        self.ssh.sendline(response)
            except pexpect.EOF:
                self._report(output, out_stream=out_stream, verbose=verbose)
                break
        self.ssh.prompt(timeout=0.1)
        self._report(output, out_stream=out_stream, verbose=verbose)
        return ''.join(output).split("\n")

    # noinspection PyUnusedLocal,PyShadowingNames
    def run(self, cmd_args, out_stream=sys.stdout, env=None, verbose=True,
            prefix=None, postfix=None, accept_defaults=False, pattern_response=None, timeout=120,
            timeout_interval=.001, debug=False):
        """
        Runs the command and returns the output, writing each the output to out_stream if verbose is True.

        :param cmd_args: list of command arguments or str command line
        :type cmd_args: list or str
        :param out_stream: the output stream
        :type out_stream: file
        :param env: the environment variables for the command to use.
        :type env: dict
        :param verbose: if verbose, then echo the command and it's output to stdout.
        :type verbose: bool
        :param prefix: list of command arguments to prepend to the command line
        :type prefix: list[str]
        :param postfix: list of command arguments to append to the command line
        :type postfix: list[str]
        :param accept_defaults: accept responses to default regexes.
        :type accept_defaults: bool
        :param pattern_response: dictionary whose key is a regular expression pattern that when matched
            results in the value being sent to the running process.  If the value is None, then no response is sent.
        :type pattern_response: dict[str, str]
        :param timeout: the maximum time to give the process to complete
        :type timeout: int
        :param timeout_interval: the time to sleep between process output polling
        :type timeout_interval: int
        :param debug: emit debugging info
        :type debug: bool

        :returns: the output of the command
        :rtype: str
        """
        if isinstance(cmd_args, str):
            # cmd_args = pexpect.split_command_line(cmd_args)
            cmd_args = [cmd_args]

        if pattern_response or accept_defaults or self.accept_defaults:
            return self.run_pattern_response(cmd_args, out_stream=out_stream, verbose=verbose,
                                             prefix=prefix, postfix=postfix,
                                             pattern_response=pattern_response,
                                             accept_defaults=accept_defaults or self.accept_defaults,
                                             timeout=timeout)

        args = self.expand_args(cmd_args, prefix=prefix, postfix=postfix)
        command_line = ' '.join(args)
        self.display("{line}\n".format(line=command_line), out_stream=out_stream, verbose=verbose)
        self.ssh.prompt(timeout=.1)  # clear out any pending prompts
        self.ssh.sendline(command_line)
        self.ssh.prompt(timeout=timeout)
        buf = [self.ssh.before]
        if self.ssh.after:
            buf.append(str(self.ssh.after))
        return ''.join(buf)

    def put(self, files, remote_path=None, out_stream=sys.stdout, verbose=False):
        """
        Copy a file from the local system to the remote system.

        :param files:
        :param remote_path:
        :param out_stream:
        :param verbose:
        :return: :rtype:
        """
        if remote_path is None:
            remote_path = files
        self.display("scp '{src}' '{dest}'".format(src=files, dest=remote_path),
                     out_stream=out_stream, verbose=verbose)
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.address, self.port, self.user, self.password)
        scp = SCPClient(ssh.get_transport())
        # scp = SCPClient(self.ssh.get_transport())
        output = scp.put(files, remote_path, recursive=True) or ''
        self.display("\n" + output, out_stream=out_stream, verbose=verbose)
        return output

    def get(self, remote_path, local_path=None, out_stream=sys.stdout, verbose=False):
        """
        Copy a file from the remote system to the local system.

        :param remote_path:
        :param local_path:
        :param out_stream:
        :param verbose:
        :return: :rtype:
        """
        if local_path is None:
            local_path = remote_path
        self.display("scp '{src}' '{dest}'\n".format(src=remote_path, dest=local_path),
                     out_stream=out_stream, verbose=verbose)

        names = [name.strip() for name in self.run(['/bin/ls', '-1', '--color=never', remote_path]).split('\r\n')[1:] if
                 name.strip() != '[PEXPECT]$']
        self.display("names: {names}".format(names=repr(names)))

        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.address, self.port, self.user, self.password)
        # scp = SFTPClient.from_transport(ssh.get_transport())
        # output = scp.get(remote_path, local_path, recursive=True)

        ftp = ssh.open_sftp()
        for name in names:
            self.display(name + '\n')
            ftp.get(name, local_path)

        output = repr(names)
        self.display(output, out_stream=out_stream, verbose=verbose)
        return output

    def _system(self, command_line):
        self.ssh.sendline(command_line)
        self.ssh.prompt()
        buf = [self.ssh.before]
        if self.ssh.after:
            buf.append(str(self.ssh.after))
        return ''.join(buf)

    def logout(self):
        """
        Close the ssh session.
        """
        if self.ssh:
            self.ssh.logout()
            self.ssh = None

    def getUserFromCredsFile(self, host):
        # noinspection PyArgumentEqualDefault
        with open(self.creds_file, 'r') as creds_file:
            creds_dict = json.loads(creds_file.read())
            if host in creds_dict:
                if 'user' in creds_dict[host]:
                    return creds_dict[host]['user']['name']

    def getPasswordFromCredsFile(self, host, user):
        # noinspection PyArgumentEqualDefault
        try:
            # noinspection PyArgumentEqualDefault
            with open(self.creds_file, 'r') as creds_file:
                creds_dict = json.loads(creds_file.read())
                if host in creds_dict:
                    if 'user' in creds_dict[host]:
                        if creds_dict[host]['user'] == user:
                            return creds_dict[host]['password']
        except Exception as ex:
            debug(str(ex))
        return None

    def getUser(self, host):
        user = self.getUserFromCredsFile(host)
        if user is None or not user:
            user = getuser()
        return user

    def getPassword(self, host, user):
        password = self.getPasswordFromCredsFile(host, user)
        if password is None or not password:
            password = getpass('password for {user}@{host}: '.format(user=user, host=host))
            self.saveUserPasswordToCredsFile(host, user, password)
        return password

    def saveUserPasswordToCredsFile(self, host, user, password):
        creds_dict = {}
        # noinspection PyBroadException
        try:
            # noinspection PyArgumentEqualDefault
            with open(self.creds_file, 'r') as creds_file:
                creds_dict = json.loads(creds_file.read())
        except:
            pass
        if host not in creds_dict.keys():
            creds_dict[host] = {}
        creds_dict[host]['user'] = user
        creds_dict[host]['password'] = password
        mode = stat.S_IWUSR | stat.S_IRUSR
        # noinspection PyBroadException
        try:
            mode = os.stat(self.creds_file).st_mode
        except:
            # noinspection PyBroadException
            try:
                touch(self.creds_file)
            except:
                pass
        # noinspection PyBroadException
        try:
            os.chmod(self.creds_file, mode | stat.S_IWUSR | stat.S_IWRITE)
            with open(self.creds_file, 'w') as out_file:
                json.dump(creds_dict, out_file)
            os.chmod(self.creds_file, mode)
        except:
            pass
