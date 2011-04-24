#!/usr/bin/env python

# http://www.hawkee.com/snippet/2497/

import socket
import re
import time
import sys
import os

import config # We load configuration data.


'''This is a global function, to avoid bot hangs.'''
def upgrade():
    '''Performs code upgrade, beware the bugs!'''
    print "reloading"
    import xreload
    reload(xreload)
    import bot_module
    xreload.xreload(bot_module)
    return


class Bot():

    SOCKET_TIMEOUT = 300
    DELAY_RECONNECTION = 600

    # TODO: Load available configurations from file.
    # TODO: Select first configuration available as default.
    # TODO: Reconnect with one param, changes configuration.
    # TODO: Every configuration will have a name to identify it.

    # TODO: Change owner into a list.

    # Default configuration.
    network = 'irc.freenode.org'
    port = 6667
    nick = 'ztn'
    channel = ['#boofar', '#emacs-es']
    owner = 'Zenton'

    log_file = 'log_'
    log_f = None

    # TODO Create a config class containing configuration and log?

    def close_log_file(self):
        if self.log_f is not None:
            self.log_f.close()

    def open_log_file(self, cfg):
        self.close_log_file()
        if os.path.isfile(self.log_file + cfg):
            flag = 'a'
        else:
            flag = 'w'
        self.log_f = open(self.log_file + cfg, flag, 0)

    # TODO: Use self.cfg to store configuration structure.
    #   self.cfg.network, self.cfg.port, etc
    #   self.cfg.tell_dict = None # Default.
    def load_config(self, cfg_string):
        if cfg_string in config.config_dict.keys():
            print "setting new conf: ", cfg_string
            cfg = config.config_dict[cfg_string]
            self.network = cfg['network']
            self.port = cfg['port']
            self.nick = cfg['nick']
            self.channel = cfg['channel']
            self.owner = cfg['owner']
            self.open_log_file(cfg_string)
            self.config = cfg_string
            return True
        else:
            return False

    # TODO: Dictionary configuration should contain tell list.
    # TODO: Connection should contain command list and data buffer.
    # TODO: Every connection should be initialized using one configuration.

    def __init__(self, configuration='freenode'):
        self.quit_bot = False
        self.time_init = time.time() # get initial time in seconds.
        self.rexp_general = re.compile(r'^(:[^ ]+)?[ ]*([^ ]+)[ ]+([^ ].*)?$')

        # First time we connect without delay.
        self.reconnect = True  
        self.connect_delay = False
        self.irc = None
        self.config = None
        self.load_config(configuration)
        self.tell_dict = {}

    def send(self, message):
        '''Sends message string through socket and adds CR LF at the end.'''
        self.irc.send('%s\r\n' % message)
        self.log_f.write('>>%s\n' % message)

    def msg(self, channel_to, message):
        '''Shows via channel_to message text.
        message should not contain first : and last CR LF'''
        self.send('PRIVMSG %s :%s' % (channel_to, message))

    def long_msg(self, channel_to, message):
        '''Shows a message containing several lines'''
        for line in message.split('\n'):
            self.msg(channel_to, line)

    def connect_to_server(self):
        self.reconnect = False
        self.connect_delay = False
        self.command_list = []  # Reset command list.
        self.data_buffer = ''  # Reset data received buffer.
        self.irc = socket.socket ( socket.AF_INET, socket.SOCK_STREAM )        
        # Set timeout when connecting.
        print "Connecting to server now..."
        self.irc.settimeout(self.SOCKET_TIMEOUT)
        self.irc.connect ( ( self.network, self.port ) )

        self.send('NICK ' + self.nick)
        self.send('USER ' + self.nick + ' Zbot Zbot :Python IRC Bot')
        for ch in self.channel:
            self.send('JOIN ' + ch)
        
    def disconnect(self):
        if self.irc is not None:
            print "Disconnecting..."
            try:
                self.irc.shutdown(socket.SHUT_RDWR)
                self.irc.close()
            except socket.error:
                pass
                #self.connect_delay = True

            self.irc = None

    def say_hello(self):
        # Say hello to owner!
        self.msg(self.owner, 'Hello World.')
    
    def get_uptime(self):
        time_actual = time.time()
        uptime_seconds = long(time_actual - self.time_init)
        return self.format_time(uptime_seconds)

    def format_time(self, seconds, precission=5, abbrev=False):
        if seconds == 0:
            return '0 seconds'
        
        if abbrev == False:
            names = ['second', 'minute', 'hour', 'day', 'year']
        else:
            names = ['s', 'm', 'h', 'd', 'y']
            
        lasting = [60, 60, 24, 365]
        res = []
        for i in lasting:
            res.append(seconds % i)
            seconds /= i
        res.append(seconds)
        
        result = []
        names.reverse()
        for i in names:
            n = res.pop()
            cad = str(n) + ' ' + i
            if n != 1 and not abbrev:
                cad += 's'
            if n != 0:
                result.append(cad)
                
        length = len(result)
        if precission > length:
            precission = length

        if precission > 1:
            r = ', '.join(result[0:precission-1]) + ' and ' + result[precission-1]
            return r
        else:
            return result[0]


    def prefix_get_nick(self, prefix):
        if prefix is None:
            return None

        p = re.search('^:([^ ]+)!', prefix)
        if p is None:
            return None
        else:
            r = p.groups()
            return r[0]

    def get_params(self, params):
        """Returns a list containing params split correctly."""
        p = re.search(r'([^ :]+)*[ ]*(:.*$)?', params)
        if p is not None:
            result = p.groups()
        else:
            result = None
        print "params: ", result
        return result


    def check_privileges(self, who, channel_to):
        '''If user is not in the owner ring, or is not the owner,
        it sends a non privileges message, and returns False.
        Other wise it return true.'''
        
        if who is None or who != self.owner:
            # who has no privileges enough.
            print "%s :Not enough privileges" % who
            self.msg(channel_to, '%s: you do not have enough privileges.\r\n' % who)
            return False
        else:
            return True

        
    # TODO: code cmd_three_p function   command first_without_space long_till_end_of_line.
    # TODO: SHOULD I CREATE A cmd_one_p(message) function instead?
    # TODO: THINK ABOUT CREATING AN ONLY COMMAND SEARCHING FUNCTION, PREVIOUSLY INITIALIZED.

    def cmd_one_p(self, command, message, case_insensitive=True):
        # TODO: Think about compiling these command expressions.

        cmd_str = r'^:([ ]*!|[ ]*%s:[ ]*!)[ ]*(%s)' % (self.nick, command)

        if case_insensitive == True:
            p = re.search(cmd_str, message, re.IGNORECASE)
        else:
            p = re.search(cmd_str, message)
        
        if p is None:
            return None
        else:
            return p.groups()

    def cmd_two_p(self, command, message, case_insensitive=True):

        cmd_str = r'^:([ ]*!|[ ]*%s:[ ]*!)[ ]*(%s)[ ]+([^ ].*)[ ]*$' % (self.nick, command)

        if case_insensitive == True:
            p = re.search(cmd_str, message, re.IGNORECASE)
        else:
            p = re.search(cmd_str, message)

        if p is None:
            return None
        else:
            return p.groups()


    def cmd_three_p(self, command, message, case_insensitive=True):

        cmd_str = r'^:([ ]*!|[ ]*%s:[ ]*!)[ ]*(%s)[ ]+([^ ]+)[ ]+([^ ].*)[ ]*$' % (self.nick, command)

        if case_insensitive == True:
            p = re.search(cmd_str, message, re.IGNORECASE)
        else:
            p = re.search(cmd_str, message)

        if p is None:
            return None
        else:
            return p.groups()


    def cmd_general_p(self, command, message, case_insensitive=True):

        cmd_str = r'%s' % command

        if case_insensitive == True:
            p = re.search(cmd_str, message, re.IGNORECASE)
        else:
            p = re.search(cmd_str, message)

        if p is None:
            return None
        else:
            return p.groups()


    def parse_command(self, data):
        ppp = self.rexp_general
        r = ppp.match(data)
        if r is None:
            # command does not match.
            print "command does not match."
            return

        g = r.groups()
        print g
        prefix = g[0]
        cmd = g[1]
        params = g[2]

        who = self.prefix_get_nick(prefix)
        print "nick: ", who

        # Only for debug.
        self.get_params(params)


        if cmd == 'PING':
            self.send('PONG %s' % params)
            return
        
        elif cmd == 'NICK':
            if who == self.nick:
                par = self.get_params(params)
                new_nick = par[1]
                if new_nick is not None:
                    self.nick = new_nick[1:] # we discard first :
                    print "new nick: ", self.nick
                    return

        #elif cmd == 'KICK':
        #    self.irc.send('JOIN ' + self.channel + '\r\n')

        elif cmd == 'JOIN':
            who = self.prefix_get_nick(prefix)
            if who in self.tell_dict:
                for m in self.tell_dict[who]:
                    self.msg(who, m)
                del self.tell_dict[who]
            return    
            
        elif cmd == 'PRIVMSG':

            par = self.get_params(params)

            if par is None:
                return

            channel_from = par[0]
            print "ch: ",channel_from
            if channel_from == self.nick:
                # we are in a private channel.
                channel_to = who
            else:
                channel_to = channel_from

            message = par[1]
            print "msg: ", message


            # TODO: IMPORTANT: WE SHOULD CHECK FIRST FOR cmd_two_p commands before cmd_one_p.
            

            p = self.cmd_one_p(r'upgrade', message)
            if p is not None:
                if self.check_privileges(who, channel_to):
                    upgrade()
                    # TODO: IMPORTANT: INITIALIZE WHATEVER IS NEEDED TO BE INITIALIZED HERE.
                    self.open_log_file(self.config)
                return

            r = self.cmd_three_p(r'sayc', message)
            if r is not None:
                print "sayc: ", r
                self.msg(r[2], r[3])
                return

            r = self.cmd_three_p(r'tell', message)
            if r is not None:
                print "tell: ", r
                if r[2] not in self.tell_dict:
                    self.tell_dict[r[2]] = [r[3]]
                else:
                    self.tell_dict[r[2]].append(r[3])
                return

            r = self.cmd_two_p(r'say', message)
            if r is not None:
                print "say: ", r
                if r[2] is not None:
                    self.msg(channel_to, r[2])
                return

            p = self.cmd_one_p(r'quit', message)
            if p is not None:
                if self.check_privileges(who, channel_to):
                    # who is self.owner
                    self.msg(self.owner, 'Fine, if you dont want me')
                    self.send('QUIT')
                    self.quit_bot = True
                return

            r = self.cmd_two_p(r'part', message)
            if r is not None:
                print "part: ", r
                if r[2] is not None:
                    self.send('PART ' + r[2])
                return

            r = self.cmd_one_p(r'part', message)
            if r is not None:
                print "part: ", r
                if channel_from != self.nick:
                    self.send('PART ' + channel_from)
                return

            r = self.cmd_two_p(r'help', message)
            if r is not None:
                print "help: ", r
                help_cmd = r[2]
                help_str = None

                if help_cmd == 'quit':
                    help_str = '  !quit  -- quits the bot. You need to be the bot owner.'
                elif help_cmd == 'part':
                    help_str = '''  !part  -- lefts this channel.
!part  channel[,channel]*  -- lefts those channels.'''
                elif help_cmd == 'join':
                    help_str = '  !join  channel[,channel]*  -- joins those channels.' 
                elif help_cmd == 'help':
                    help_str = '''  !help  -- shows general help.
  !help command -- shows specific help for that command.'''
                elif help_cmd == 'hello':
                    help_str = '  hi|hello|HI %s -- it answers saying hello to you.' % self.nick
                elif help_cmd == 'uptime':
                    help_str = '  !uptime -- shows how long bot has been running.'
                elif help_cmd == 'upgrade':
                    help_str = '  !upgrade -- reloads code changes and continue executing.'
                elif help_cmd == 'nick':
                    help_str = '  !nick new_nick -- changes bot nick.'
                elif help_cmd == 'say':
                    help_str = '  !say text -- writes that text in the same channel you are.'
                elif help_cmd == 'sayc':
                    help_str = '  !sayc channel text -- writes that text in channel.'
                elif help_cmd == 'tell':
                    help_str = '''  !tell who text -- when who joins to a channel where the bot is,
it sends him a private message showing text.'''
                elif help_cmd == 'reconnect':
                    help_str = '''  !reconnect -- reconnects to same network and same configuration.
  !reconnect new_config -- reconnects using new_cofig configuration.'''

                if help_str is not None:
                    self.long_msg(channel_to, help_str)
                
                return

            r = self.cmd_one_p(r'help', message)
            if r is not None:
                print "help: ", r
                help_str = '''Command list:
part, join, help, uptime, say, sayc, tell
.
Administrative commands:
quit, upgrade, nick, reconnect
.
Command invocation:
 !quit 
 %s: !quit
.
Commands are case insensitive.
.
Use <<!help command>> for a more command specific help.''' % self.nick
                self.long_msg(channel_to, help_str)
                return

            r = self.cmd_two_p(r'join', message)
            if r is not None:
                print "join: ", r
                if r[2] is not None:
                    self.send('JOIN ' + r[2])
                return

                    
            r = self.cmd_one_p(r'uptime', message)
            if r is not None:
                uptime_str = self.get_uptime()
                print "us: ", uptime_str
                self.msg(channel_to, uptime_str)
                return

            r = self.cmd_two_p(r'nick', message)
            if r is not None:
                if self.check_privileges(who, channel_to):
                    print "nick: ", r
                    if r[2] is not None:
                        self.send('NICK ' + r[2])
                return

            r = self.cmd_two_p(r'reconnect', message)
            if r is not None:
                if self.check_privileges(who, channel_to):
                    print "reconnect: ", r
                    if r[2] is not None:
                        cfg = (r[2]).rstrip()
                        if self.load_config(cfg):
                            self.reconnect = True
                return


            r = self.cmd_one_p(r'reconnect', message)
            if r is not None:
                if self.check_privileges(who, channel_to):
                    self.reconnect = True
                    self.open_log_file(self.config)
                return

            p = self.cmd_general_p(r'(hi|HI|hello|hola)[ ]+%s' % self.nick, message)
            if p is not None:
                self.msg(channel_to, 'Hi %s, nice to meet you!' % who)
                return

            p = self.cmd_general_p(r'(bye|chao|adios)[ ]*$', message)
            if p is not None:
                print "chao :" + who + " " + channel_to
                if who == self.owner or who == 'Vejeta':
                    self.msg(channel_to, 'Bye bye %s!' % who)
                return

    def get_command(self):

        if len(self.command_list) > 0:
            result = self.command_list.pop(0)
            return result

        # There is no command available, we read more bytes.
        # We set a timeout:
        print "asking for socket data..."
        self.irc.settimeout(self.SOCKET_TIMEOUT)
        chunk = self.irc.recv(4096)


        if chunk == '':
            print "NO DATA RECEIVED, RAISING TIMEOUT"
            raise socket.timeout()

        self.data_buffer = ''.join([self.data_buffer, chunk])

        self.command_list = self.data_buffer.split('\r\n')
        self.data_buffer = self.command_list.pop()
        if len(self.command_list) == 0:
            return None

        result = self.command_list.pop(0)
        return result



    def main(self):

        # Emergency upgrade.
        import signal
        signal.signal(signal.SIGQUIT, lambda signum, stack_frame: upgrade())

        # Main loop.
        while True:
            try:
                if self.reconnect == True:
                    # reconnecting
                    self.disconnect()
                    if self.connect_delay == True:
                        print "reconnecting after %s seconds" % self.DELAY_RECONNECTION
                        time.sleep(self.DELAY_RECONNECTION)
                    self.connect_to_server()
                    self.say_hello()
                    

                com = self.get_command()
                while com is None:
                    com = self.get_command()
                print "com: ", com
                self.log_f.write(com + '\n')

                self.parse_command(com)
                if self.quit_bot == True:
                    break

            
            except socket.error:
                # waits self.DELAY_RECONNECTION secs and tries to connect again.
                # Catches socket.error: [Errno 110] Connection timed out
                self.reconnect = True
                self.connect_delay == True

            except socket.timeout:
                # Server seems to be down, because it says nothing.
                print "socket.timeout: server does not respond."
                self.reconnect = True

            except KeyboardInterrupt:
                # We finish if ctr-c is sent to the bot.
                print "KeyboardInterrupt"
                break
                
            except:
                print "An exception happened: "
                (ex_type, ex_value, ex_traceback) = sys.exc_info()
                sys.excepthook(ex_type, ex_value, ex_traceback)
                sys.exc_clear()

        # Before ending closes the socket, and log file.
        self.disconnect()
        self.close_log_file()
