#! /usr/bin/env /usr/bin/python

'''
< Bot> IrcUser, 2#2d2+2d2+2d2+2: 9 [2d2=1,2; 2d2=1,1; 2d2=1,1], 10 
              [2d2=1,1; 2d2=1,2; 2d2=2,1]
'''


#import sys
import random
import re
import cStringIO

DICEMAX = 100000  # will not roll more dice
ROUNDSMAX = 10   # will not roll more rounds
DISPLAYMAX = 8  # will not display individual rolls for dice > x

rand = random.Random()
rand.seed()

'''
#rex = re.compile("4#1df4 full|brief", re.I)
rex = re.compile("^((\d+)#)?(\d+)?d(\d+)([\+-]\d+)?(\s+(.*\S)\s*)?$", re.I)
'''

# dice string with fluff
# 4#d9d+d9d+d9d fluff
#^((?P<numrounds>\d+)#)?(?P<dicestuff>[+-\dd]+)(\s+(?P<fluff>.*))?
#rexmain = re.compile("^((?P<numrounds>\d+)#)?(?P<dicestuff>[+-\dd]+)(\s+(?P<fluff>.*[^\s])\s*)?")
rexmain = re.compile("^((?P<numrounds>\d+)#)?(?P<dicestuff>[-+\dd]+)(\s+(?P<fluff>.*\S))?\s*$", re.I)

# one set
#+4d4
# (?P<adder>[+-])
# (?P<numdice>\d+)?
# (?P<dtoken>d)?
# (?P<numsides>\d+)?
rexset = re.compile("(?P<adder>[+-])(?P<numdice>\d+)?(?P<dtoken>d)?(?P<numsides>\d+)?", re.I)


# returns (result, [roll1, roll2, ...])
def rollsingle(neg = False, dice = 1, sides = 6):
    global rand

    if(dice < 1 or dice > DICEMAX): return False  # display ERROR message

    n = 0
    rols = []

    if sides == 0:
        n = dice
    else:
        for _ in xrange(dice):
            i = rand.randint(1,sides)
            rols.append(i)
            n += i

    return ( (n * -1 if neg else n), rols)

# input string "+1d2+3d4-d5-6d+7"
#output:
#[actualstring
# total
# [ #tallys
#  (result, [roll1, roll2, ...]),
#  ...
# ]
#]
def rollround(stuff):
    instring = '+' + stuff  #will be ignored if redundant

    tallys = []
    actualstring = cStringIO.StringIO()

    groups = rexset.findall(instring)
    #subgroupnames are lost here. oh well.
    for group in groups:
        adder = group[0]
        numdice = group[1]
        dtoken = group[2]
        numsides = group[3]

        if not numdice and not dtoken and not numsides:
            continue   # sigh

        numdice = int(numdice) if numdice else -1
        numsides = int(numsides) if numsides else 6

        if(dtoken):
            if numdice == -1: numdice = 1
        else:
            numsides = 0   # indicate flat number
            numdice = int(numdice) if numdice else -1

        single = rollsingle(neg=adder!='+',dice=numdice, sides=numsides)
        if(single):
            tallys.append(single)
        else:
            return None  # display ERROR message


        actualstring.write(adder)
        actualstring.write("%d" % numdice) # or simple int
        if(dtoken):
            actualstring.write('d')
            actualstring.write("%d" % numsides)

    if len(tallys) < 1:
        return None  # 3#+-+-+-+

    total = 0
    for r in tallys:
        total += r[0]
    actualstring = actualstring.getvalue()
    if actualstring[0] == '+': actualstring = actualstring[1:]
    return [actualstring, total, tallys]

# return entire output string, or None if no match, or error string if bad match
def parsemain(line):
    mat = rexmain.match(line)
    if not mat: return None  # no dice

    dicestuff = mat.group('dicestuff')
    if not dicestuff:
        return "This message should be impossible"

    rounds = mat.group('numrounds')
    if not rounds and not re.search('d', dicestuff, re.I):
        return None   # line simply starts with a number and/or +-
    rounds = int(rounds) if rounds else 1

    if rounds < 1 or rounds > ROUNDSMAX:
        return "error: rounds > %d" % ROUNDSMAX

    holding = cStringIO.StringIO()
    actualstring = ''

    for _ in xrange(rounds):
        current = rollround(dicestuff)
        if not current:
            return "error: bad dice string (numdice > %d?)" % DICEMAX

        actualstring = current[0]
        current.pop(0)

        num = current[0]
        current.pop(0)

        current = current[0]

        for i in xrange(len(current)):
            l = len(current[i][1])
            if l < 2:
                current[i] = "(%d)" % current[i][0]
            if  l > DISPLAYMAX:
                current[i] = current[i][0],

        current = str(current)
        current = current.replace("'", "")

        holding.write('  ' + chr(2) + str(num) + chr(2) + ' ')  #bold
        holding.write(current)



    out = cStringIO.StringIO()
    if rounds != 1:
        out.write("%d#" % rounds)
    out.write(actualstring)
    if mat.group('fluff'): out.write(" (%s)" % mat.group('fluff'))
    out.write(':')
    out.write(holding.getvalue())

    return out.getvalue()



def dicehelp():
    return "Dice Syntax: 2#3d4-5d6+7 I'm casting mogic mossile"



if __name__ == "__main__":
    import sys
    '''
    if len(sys.argv) < 4:
        print "USAGE: pydice <rounds> <dice> <sides>"
        exit(0)
    print roll(int(sys.argv[3]),int(sys.argv[2]),int(sys.argv[1]))
    '''

    if len(sys.argv) > 1:
        print sys.argv[1] + '\n-----'
        #print rollround(sys.argv[1])
        print parsemain(sys.argv[1])

