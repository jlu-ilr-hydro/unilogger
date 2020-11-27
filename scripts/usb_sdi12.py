#! /usr/bin/python3
import sys
import serial
import asyncio
import time

from unilogger.bus import sdi12, open_bus

def console(port):
    """
    Starts an interactive console for SDI12 commands
    """
    def isint(s):
        try:
            i = int(s)
            return True
        except:
            return False
    s = serial.Serial(port, baudrate=9600, timeout=1)
    s.read(100)

    while True:
        print('Enter SDI command in the form aX!, eg. 2I!')
        print('q to quit')
        cmd = input('Command:').strip()
        if cmd.lower().startswith('q'):
            break
        elif cmd.endswith('!'):
            s.write((cmd + '\r\n').encode())
            response = s.readline()
            print(' -> ', response.decode().strip())
        else:
            print('Command did not end with !')


async def scanbus(port):
    if len(sys.argv) > 3:
        out = open(sys.argv[3], 'w')
    else:
        out = sys.stdout
    print('Create bus')
    bus = sdi12.Bus(port)
    bus.debug = True
    print('SDI12 bus open on', port)
    bus.sensors = await bus.scanbus('012')

    bus.to_stream(out)


async def readbus(busfile):

    bus = open_bus(busfile)
    print(bus)
    print(time.ctime())
    values = await bus.read_all()
    for v in values:
        print(v)

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1].startswith('h'):
        print('Usage: test/usb_sdi12.py [csr] [port] [busfile]')
        print('   c: opens a SDI12 console on port [port]')
        print('   s: Scans the bus at port [port] and writes a new busfile [busfile]')
        print('        eg. test/usb_sdi12.py s /dev/ttyUSB4 preferences/sdi12.bus.yaml')
        print('   r: Reads actual data using the busfile, eg. test/usb_sdi12.py r preferences/sdi12.bus.yaml')
    elif sys.argv[1] == 'c':
        console(sys.argv[2])
    elif sys.argv[1] == 's':
        asyncio.run(scanbus(sys.argv[2]))
    elif sys.argv[1] == 'r':
        asyncio.run(readbus(sys.argv[2]))

