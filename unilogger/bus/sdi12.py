"""
Logger bus wrapper for SDI12 devices

SDI12 specification: http://www.sdi-12.org/current%20specification/SDI-12_version-1_4-August-10-2016.pdf
"""
from . import base
import aioserial
import asyncio
import datetime
from attrdict import AttrDict
from typing import List
import contextlib

import warnings

import logging
logger = logging.getLogger(__name__)

def encode(string: str) -> bytes:
    """
    Encodes a unicode string to a bytesting with UTF-8
    :param string:
    :return:
    """
    return string.encode()


def decode(bytestring: bytes) -> str:
    """
    Decodes a bytestring to unicode assuming UTF-8
    :param bytestring:
    :return:
    """
    return bytestring.decode()


class parser:
    """
    Helper functions to parse SDI12 responses
    """
    channels = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    @staticmethod
    def M(response: str):
        """
        Parses the response to a C or M command
        :return: seconds to result, number of values
        """
        try:
            return int(response[1:4]), int(response[4:])
        except (ValueError, TypeError):
            raise RuntimeError('Expected numbers but got {}'.format(response))

    @staticmethod
    def D(response: str):
        """
        Parses the response to an SDI12 D command and yields the values
        :param response: Typical response to D command is a+xxx.x+xxx.xxx-xxx
        :return: List of float values
        """
        # Add spaces between the numbers, split the response and skip the address
        values = response.replace('+', ' +').replace('-', ' -').split()[1:]
        for value in values:
            try:
                v = float(value)
                yield v
            except (ValueError, TypeError):
                yield None


class SDI12port(aioserial.AioSerial):
    def __init__(self, port, **kwargs):
        super().__init__(port, **kwargs)
        self.lock = asyncio.Lock()

    async def __call__(self, cmd: str) -> str:
        """
        Writes string cmd to serial port and return the response as string
        :param cmd:
        :return:
        """
        with await self.lock:
            await self.write_async(encode(cmd + '\n'))
            # SDI 12 is slow, let some time pass until looking for a result
            await asyncio.sleep(0.1)
            line = await self.readline_async()
            return decode(line)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class Sensor(base.Sensor):
    """
    Wraps a sensor on a SDI12-Bus connected over the Arduino based
    SDI12 connector
    """

    def __init__(self, channel, name, values, **kwargs):
        """
        Creates a new SDI12device from the response to the aI! string
        :bus: the SDI12bus this device belongs to.
        :info: A string line response from the SDI12 aI! command
        :config: A list of dictionaries
        """
        self.channel = channel
        self.name = name
        self.extradata = kwargs
        self.valuefactories: List[base.ValueFactory] = [
            base.ValueFactory(**v)
            for v in values
        ]
        for vf in self.valuefactories:
            if not vf.name.startswith(self.name):
                vf.name = self.name + '.' + vf.name

    def __str__(self):
        return ('SDI12 device on {o.channel} is {o.name} ({c} values)'
                .format(o=self, c=len(self.valuefactories)))

    async def do_measurement(self, serial: SDI12port) -> asyncio.Task:
        """
        Starts an asynchronous measurement of the device and returns
        a task to read the measurement later with :meth:`unilogger.bus.sdi12.Sensor.read_measurement`

        SDI-Command sent: aC!
        SDI-Command of the Task: aD0!, if necessary also aD1! etc.

        :param serial: The SDI12 port
        :return: asyncio.Task to write aDX! commands
        """
        response = await serial(self.channel + 'C!\r\n')
        # get wait time and number of values for this device
        wait, nvalues = parser.M(response)
        logging.debug(f'SDI12.{self.channel}C: {nvalues} values in {wait}s')
        return asyncio.create_task(self.read_measurement(serial, wait, nvalues))

    async def read_measurement(self, serial: SDI12port, wait: float, nvalues: int) -> List[base.Value]:
        """
        Wait the wait time and performs the D0 (get data) command
        If necessary it calls also the D1, D2 etc commands
        :param serial: Write coroutine
        :param wait: Wait time in seconds
        :param nvalues: Number of values
        :return: A list of augmented Values
        """
        tstart = datetime.datetime.utcnow()
        await asyncio.sleep(wait)
        # Get the values, probably spread over several D commands
        floatvalues = []
        d = 0  # The D command number
        # repeat the D commands as necessary
        while len(floatvalues) < nvalues:
            response = await serial('{}D{}!\r\n'.format(self.channel, d))
            floatvalues.extend(parser.D(response))
            d += 1
        # Augment & transform the values
        return [factory(x, time=tstart) for
                factory, x in
                zip(self.valuefactories, floatvalues)]

    def __asdict__(self)->dict:
        res = self.extradata.copy()
        res.update(dict(channel=self.channel, name=self.name, values=[]))
        for vf in self.valuefactories:
            res['values'].append(vf.__asdict__())
        return res


class SDI12Bus(base.Bus):
    """
    Talks to configured SDI12-Sensors at this SDI12-Bus
    """

    def __init__(self, port=None, sensors=None, **kwargs):
        kwargs.pop('module', None)

        self.port = port
        self.baudrate = 9600
        self.timeout = 0.5
        self.extradata = kwargs

        self.port = port

        if sensors:
            self.sensors = [Sensor(**sensor_data) for sensor_data in sensors]

    @contextlib.contextmanager
    def open(self) -> SDI12port:
        with SDI12port(self.port, timeout=self.timeout, baudrate=self.baudrate) as port:
            yield port

    def __repr__(self):
        return 'sdi12.Bus(port={})'.format(self.port)

    async def change_address(self, old_adress, new_adress):
        with self.open() as serial:
            await serial(old_adress + 'A' + new_adress + '!')

    def makesensor(self, channel, name=None, values=None, **kwargs) -> Sensor:
        """
        Create a sensor on this bus
        :param channel: SDI12 channel ('0'..'9', 'a'..'z','A'..'Z')
        :param name: Name of the sensor
        :param values: List of dict, describing valuefactories
        :param kwargs: Extra data to describe the sensor
        :return: The created SDI12Sensor
        """
        s = Sensor(channel, name, **kwargs)
        if values:
            errors = []
            for v in values:
                try:
                    s.valuefactories.append(base.ValueFactory(**v))
                except Exception as e:
                    logging.warning(f'Problem with')
        return s

    def __asdict__(self):
        res = self.extradata.copy()
        res.update(dict(port=self.port))
        res['module'] = __name__
        res['sensors'] = []
        for s in self.sensors:
            res['sensors'].append(s.__asdict__())
        return res


    async def scanchannel(self, serial: SDI12port, channel: str) -> Sensor:
        """
        Reads on the specified SDI12 channel to create a sdi12.Sensor

        :param serial: SDI12port instance
        :param channel: SDI12 channel ('0'..'9', 'a'..'z','A'..'Z')
        :return:
        """

        logging.info('Channel: ', channel, end='\n')

        # Check channel with Acknowledge Active Command
        response = await serial(channel + '!\r\n')
        if response.strip() == channel:
            name = (await serial(channel + 'I!\r\n')).strip()
            logging.info(f'{channel} -> {name}')
            # Get number of values with C command to add valuefactories
            response = await serial(channel + 'C!\r\n')
            wait, nvalues = parser.M(response)
            # Get valuefactory stubs
            valuefactories = [
                base.ValueFactory(name='Value_{:02d}'.format(i), id=i)
                for i in range(nvalues)
            ]
            logging.info(f'     {nvalues} values in {wait} seconds')
            return self.makesensor(channel, name, valuefactories, scantime=wait)

        elif response.strip():
            warnings.warn('Queried channel {} but got {} as answer'.format(channel, response.strip()))

    async def scanbus(self, channels=parser.channels) -> List[Sensor]:
        """
        Scans the SDI12 bus on the channels and creates sensor stubs
        :param channels: A string of channel characters
        :return: List of detected sensors

        Usage:
        >>> bus = Bus('COM1')
        >>> bus.sensors = asyncio.run(bus.scanbus('01234'))
        >>> values = asyncio.run(bus.read_all())
        >>> for v in values:
        >>>     print(v)
        """
        with SDI12port(self.port, timeout=self.timeout, baudrate=self.baudrate) as serial:
            sensors = []
            for c in channels:
                sensor = await self.scanchannel(serial, c)
                if sensor:
                    sensors.append(sensor)
            return sensors

    async def read_all(self):
        """
        Reads all sensors concurrently
        :return:
        """
        return await self.readsensor(*self.sensors)


    async def readsensor(self, *sensors):
        """
        Reads the given sensor(s)
        :param sensors: SDI12 sensor objects
        :return: List of Value objects created by the sensors valuefactories
        """
        with self.open() as serial:
            # Storages for wait and value numbers
            tasklist = [(await s.do_measurement(serial)) for s in sensors]

            # Get the data from the sensors
            values = await asyncio.gather(*tasklist)
            return sum(values, [])  # slow but acceptable way to flatten list of lists


