#!/usr/bin/python3
import datetime
import sys
sys.path.append('.')

from unilogger.bus import addupi

def finddevice(tag):
    """
    Checks if a node in the addUPI response is a device
    :param tag: BeautifulSoup tag
    :return: bool
    """
    return tag.has_attr('class') and tag['class'] == 'DEVICE'


async def listdevices(bus: addupi.Bus):
    """
    Lists all devices on the bus
    """
    print('Get Devices')
    async with bus:
        soup, url = await bus.read(function='getconfig')
        devices = soup.find_all(finddevice)
        print('Found ', len(devices), ' devices')
        for dev in devices:
            print('    id={id} name={name}'.format(**dev.attrs))
        return [dev.attrs['id'] for dev in devices]


async def make_config(bus: addupi.Bus, *node_ids):
    """
    Creates configurations for device nodes (eg. RTUs)
    :param bus: the bus to configure
    :param node_ids: ID's of the device nodes
    :return:
    """
    async with bus:
        for sid in node_ids:
            s = await bus.configsensor(sid)
            print(sid, s, len(s.valuefactories), 'values')


async def print_actualdata(bus: addupi.Bus):
    print(bus)
    print('=' * 50, '\n')

    async with bus:
        for sensor in bus.sensors:
            data = await bus.readsensor(sensor)
            print('Data from ', sensor)
            print('-' * 50)
            for v in data:
                print('   ', v)


async def get_data(bus, fromdate):
    async with bus:
        return [await bus.readsensor(sensor, fromdate) for sensor in bus.sensors]


def make_bus(url, user, password, *node_ids):
    """
    Creates an addUPI bus for a  given URL and credentials
    :param url: URL of the A850 ADCON base station
    :param user: Username (normally 'root')
    :param password: Password
    :param sensor_ids: ID's of the device nodes to include (eg. RTUs)
    :return: the populated bus
    """
    bus: addupi.Bus = open_bus(url, user=user, password=password, module='unilogger.bus.addupi')
    await_coro(make_config(bus, *node_ids))
    bus.sensors.sort(key=lambda x: x.id)
    for s in bus.sensors:
        s.valuefactories.sort(key=lambda x: x.id)
    print(len(bus.sensors), 'sensors')

    for s in bus.sensors:
        print(s, len(s.valuefactories), 'values')
    return bus


def load_bus(fn):
    return open_bus(fn)


if __name__ == '__main__':
    from unilogger import await_coro
    from unilogger.bus import open_bus

    bus = make_bus()
    bus.to_stream(sys.stdout)
    await_coro(print_actualdata(bus))


