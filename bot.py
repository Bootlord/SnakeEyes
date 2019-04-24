#! /usr/bin/env /usr/bin/python

#import sys
import socket
import ssl
import time
import pydice
import re
import string

#defaults, overridden in config file
HOST = "127.0.0.1"
PORT = 6667
SSLPORT = 6697
NICK = 'SnakeEyesBot'
IDENT= 'SnakeEyesBot'
PASS = ''
CHANS= ['#BotTest',]
BUFSIZE = 4096
SOCKTIMEOUT = 120


# PASS sdfafsdf
# NICK dasdfsdf
# USER username hostname servername realname
# USER <ident> * * :(testing)
# QUIT bye bye
# JOIN chan,chan pass,pass
# PART chan
# TOPIC chan <:newtopic>
# NAMES chan
# KICK chan user <:comment>
# PRIVMSG chan :blah
# NOTICE nick :blah  // will receive no autoreply


running = True  # loop control, set false to trigger exit
connected = False  # loop control
regd = False
sock = None
logf = None
cmdrex = re.compile('^@@@(\w+)\s+(.+\S)\s*$')
helprex = re.compile('^(\'|\!|@@@)help', re.I)

def log(s):
    global logf
    #t = time.strftime('(%H:%M:%S)')
    t = time.strftime('(%T)')
    print t,s
    if logf:
        logf.write('%s %s\r\n' % (t, s))

# TODO: test broken connection here?
#       return false on error?
def rawsend(rawline, silent = False):
    global sock
    if not silent:
        log('RAWSEND>> '+rawline)
    sock.send(rawline + '\r\n')

def connect():
    global sock
    try:
        #sock = socket.create_connection( (HOST,PORT), timeout = SOCKTIMEOUT)
        #changed 2019/03 to attempt ssl
        sock = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        sock.settimeout(SOCKTIMEOUT)
        sock.connect( (HOST,SSLPORT) )
    except socket.error as e:
        log("Exception on socket create: " + repr(e))
        exit(e.errno)
    except:
        log('other error')

    t = time.strftime('%Y %h %T')
    log('---- SESSION START %s ----' % t)

    log('sock connected')

    # PASS sdfafsdf
    if PASS:
        rawsend('PASS ' + PASS)

    # NICK dasdfsdf
    rawsend('NICK '+NICK)

    # USER username hostname servername realname
    # USER <ident> * * :(testing)
    rawsend('USER '+IDENT+' * * :(testing)')

    #rawsend('PING :idunno')
    #time.sleep(1)
    #rawsend('PRIVMSG HostServ :ON')

    log(NICK+' reginfo sent')


def joinall():
    # JOIN chan,chan pass,pass
    for c in currentchans:   # only reading, so dont need global
        log('joining ' + c)
        rawsend('JOIN '+c)

def listenloop():
    doping = False
    global sock
    global regd
    buf = ''
    lines = []
    while True:
        try:
            buf = buf + sock.recv(BUFSIZE)
        except socket.error as e:
            log("Exception during listenloop: " + repr(e))
            doping = True
        if doping:
            doping = False
            #rawsend('PING :test', silent = True)
            rawsend('PING :test')
            continue
        lines = buf.split('\r\n')
        buf = lines.pop()
        for l in lines:
            p = process(l)
            if not p:
                return None
            # DIRTY HACK
            #if (not regd) and p == 2:
            #    regd = True
            #    time.sleep(1)
            #    joinall()

def parsemsg(line):
    b = ''
    a = line.split(':', 1)
    sender = None
    msg = {}
    if not a[0]:
        # broken connection?
        if len(a) < 2:
            return None
        # ':sender command arg arg :stuf'
        a = a[1].split(':', 1)
        sender = a[0].split(' ', 1)
        if len(sender) > 1:
            a[0] = sender[1]
        sender = sender[0]
    if len(a) > 1:
        b = a[1]
    a = filter(None, a[0].split(' '))
    #a = a[0].split(' ')
    msg["message"] = b
    msg['type'] = a.pop(0)

    msg['fromhost'] = ''
    msg['fromuser'] = ''
    msg['fromnick'] = ''
    if sender:
        sender = sender.split('@', 1)
        if len(sender) > 1:
            msg['fromhost'] = sender[1]
        sender = sender[0].split('!', 1)
        if len(sender) > 1:
            msg['fromuser'] = sender[1]
        msg['fromnick'] = sender[0]

    msg['args'] = a

    return msg


def process(line):
    rep = ''
    msg = parsemsg(line)
    if not msg:
        return None
    #print ',,,,,,,,',msg
    if msg['type'] == 'PING':
        rep = 'PONG :' + msg['message']
        rawsend(rep, silent = True)
        return 2
    elif msg['type'] == 'PONG':
        return True
    log(line)
    # TODO? possible to kick based on hostmask rather than nick?
    if msg['type'] == 'KICK' and string.lower(NICK) == string.lower(msg['args'][1]):
        c = string.lower(msg['args'][0])
        curchans_remove(c)
    # :SenderNick!name@domain.host INVITE BotNick :#ChannelName
    if msg['type'] == 'INVITE' and string.lower(NICK) == string.lower(msg['args'][0]):
        c = string.lower(string.strip(msg['message']))
        reply(msg, "Attempting to join %s" % c)
        curchans_add(c)
        rawsend('JOIN %s' % c)
    elif msg['type'] == 'PRIVMSG':
        response = pydice.parsemain(msg['message'])
        if response:
            reply(msg, response)
        elif handlecommand(msg):
            pass
    return True

# test if msg contains a command, then execute it
def handlecommand(msg):
    c = None
    comm = None
    if(helprex.match(msg['message'])):
        comm = 'help'
    else:
        c = cmdrex.match(msg['message'])
    if c:
        comm = string.lower(c.group(1))
        args = string.lower(c.group(2))
        args = args.replace(',', ' ')
        args = re.sub("\s+", ' ', args)
        args = args.split(' ')
    if comm:
        if 'help' == comm:
            #TODO
            reply(msg, bothelp())
            reply(msg, pydice.dicehelp())
            #reply(msg, "(Help message goes here.)")
        elif 'join' == comm:
            for a in args:
                reply(msg, "Attempting to join %s" % a)
                curchans_add(a)
                rawsend('JOIN %s' % a)
        elif 'part' == comm:
            for a in args:
                reply(msg, "Attempting to leave %s" % a)
                curchans_remove(a)
                rawsend('PART %s' % a)
        else:
            reply(msg, "wat is %s?" % comm)


# inmsg: a msg struct
# whatyousay: the string to send
def reply(inmsg, whatyousay):
    to = inmsg['args'][0]
    if string.lower(NICK) == string.lower(to):  # private, send to user nick 'fromnick'
        to = inmsg['fromnick']
    # else public, send to channel 'to'

    s = 'PRIVMSG %s :%s: %s' % (to, inmsg['fromnick'], whatyousay)
    rawsend(s)

def curchans_add(s):
    global currentchans
    s = string.lower(s)
    if s not in currentchans:
        currentchans.append(s)

def curchans_remove(s):
    global currentchans
    s = string.lower(s)
    if s in currentchans:
        currentchans.remove(s)

def bothelp():
    s = '[' + NICK + ' syntax]: @@@command param1 param2. '
    s += '[Commands]: help join part.'
    return s



# ------- end functions -------

# set params: nick server etc
with open('pybot.conf') as f:
    exec(f.read())

currentchans = map(string.lower, CHANS)
logname = time.strftime('%Y.%m.%d.%s.txt')
with open('log/'+logname, mode = 'a', buffering = 1) as logf:
    while running:
        connect()
        time.sleep(2)
        joinall()    # see DIRTY HACK, above
        while(listenloop()):
            pass
        log('---- connection lost ----')
        sock.shutdown(socket.SHUT_RD)
        sock.close()
        #running = False
    logf.flush()



time.sleep(3)

'''
# PRIVMSG chan :blah
sock.send('PRIVMSG '+CHAN+' :priv msg\r\n')

# NOTICE nick :blah  // will receive no autoreply
sock.send('NOTICE #Chan :noticee\r\n')

time.sleep(3)

# TOPIC chan <:newtopic>
sock.send('TOPIC '+CHAN+'\r\n')

# NAMES chan
sock.send('NAMES '+CHAN+'\r\n')

# KICK chan user <:comment>

time.sleep(3)
'''


# PART chan

# QUIT bye bye
rawsend('QUIT :bye bye')
time.sleep(1)

sock.shutdown(socket.SHUT_RD)
sock.close()
print 'socket closed'

