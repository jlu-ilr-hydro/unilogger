from datetime import datetime
import typing
import importlib
import yaml
import collections

import logging
logger = logging.getLogger(__name__)

class BusError(Exception):
    ...


class ScaleFunction:
    """
    A user defined function to scale or translate a measured value into something meaningful
    """
    def __init__(self, code: str, testvalue=None):
        if 'x' not in code:
            raise ValueError('Function code {} must include the variable x'.format(code))
        self.__code = code
        try:
            import math
            self.function = eval('lambda x:' + code, vars(math))
            if testvalue is not None:
                self.function(testvalue)
        except Exception as e:
            raise ValueError('f(1) = {} is not a valid python expression, got error: {}'
                             .format(code.replace('x', '1'), repr(e)))

    def __call__(self, x: float):
        return self.function(x)

    def __repr__(self):
        return "ScaleFunction('{}')".format(self.__code)

    def __str__(self):
        return self.__code


class Value(collections.UserDict):
    """
    A measured value with metadata
    """
    def __init__(self, value, time=None, name=None, unit=None, **kwargs):
        """
        Creates the value with meta data
        :param value: The value (a float)
        :param time: Time of measurement
        :param name: Name of measurement
        :param datasetid: Target dataset id in external database (eg- Schwingbach)
        :param kwargs: Additional meta data
        """
        self.value = value
        self.name = name
        self.time = time
        self.unit = unit
        self.extradata = kwargs

    def __str__(self):
        res = ''
        if self.name:
            res += self.name + '='
        res += '{:0.6g}'.format(self.value)
        if hasattr(self, 'unit') and self.unit:
            res += ' ' + str(self.unit)
        if self.time:
            res += self.time.strftime(' (%d.%m.%Y %H:%M:%S)')
        return res

    def __repr__(self):
        res = 'name={name!r}, time={time!r}, value={value:0.4g}'.format(**vars(self))
        if self.extradata:
            res += ', ' + ', '.join('{!s}={!r}'.format(*it) for it in self.extradata.items())
        return 'Value({})'.format(res)

    def __getattr__(self, item):
        if item in self.extradata:
            return self.extradata[item]
        else:
            raise AttributeError(f'{item} not an attribute of {self}')


    def __asdict__(self):
        """
        :return: The Value as a dictionary
        """
        res = self.extradata.copy()
        res.update(dict(name=self.name, value=self.value, time=self.time.isoformat()))
        return res

    @property
    def data(self):
        return self.__asdict__()


class ValueFactory:
    """
    A value factory is a kind of template to create a value with all needed metadata
    """

    def __init__(self, name: str = None, unit: str = None, scalefunction: typing.Union[str, ScaleFunction] = None, **kwargs):
        """

        :param name: Name of the measured item
        :param unit: Unit of the measured item
        :param scalefunction: A valid python expression to transform the raw data into the output value
        :param kwargs: Extraarguments passed to the Value
        """
        self.name = name
        self.unit = unit
        if isinstance(scalefunction, ScaleFunction):
            self.scalefunction = scalefunction
        elif scalefunction:
            self.scalefunction = ScaleFunction(scalefunction)
        else:
            self.scalefunction = None
        self.extradata = kwargs

    def __asdict__(self) -> dict:
        """
        Creates a dict describing te
        :return:
        """
        res = self.extradata.copy()
        res.update(dict(name=self.name, unit=self.unit, scalefunction=str(self.scalefunction) if self.scalefunction else None))
        return res

    def __call__(self, value: float, time=None, **kwargs) -> Value:
        """
        Creates a Value from a float
        :param value: the measured value
        :param time: A datetime of the measurement, if None, utcnow() is used
        :param kwargs: Extra meta data to be stored with the value
        :return: Value
        """
        if self.scalefunction:
            value = self.scalefunction(value)
        time = time or datetime.utcnow()
        data = self.extradata.copy()
        data.update(kwargs)
        return Value(value, time, self.name, unit=self.unit, **data)

    def __getattr__(self, item):
        if item in self.extradata:
            return self.extradata[item]
        else:
            raise AttributeError(f'{item} not an attribute of {self}')

    def __getitem__(self, item):
        if item in self.extradata:
            return self.extradata[item]
        else:
            raise KeyError(f'{item} not a data field of {self}')

    def __repr__(self):
        if self.scalefunction:
            name = str(self.scalefunction).replace('x', self.name)
        else:
            name = self.name
        return '{name} [{self.unit}]'.format(name=name, self=self)

class Sensor:
    """
    Base class for a sensor on a bus
    """
    valuefactories: typing.List[ValueFactory] = None


class Bus:
    """
    Base class for a generic bus system.
    General hierachy of the logger system:
    Bus (eg. SDI12)
    -->has sensors (eg. VAISALA @ address 0)
       -->has valuefactories (eg. Air Temp)
    """
    sensors: typing.List[Sensor] = None

    def __asdict__(self):
        raise NotImplementedError

    async def readsensor(self, sensor):
        raise NotImplementedError

    async def read_all(self) -> typing.List[Value]:
        """
        Reads all sensors
        :return: A List of Values
        """
        raise NotImplementedError


    @classmethod
    def from_dict(cls, data: dict, **kwargs):
        """
        Loads a bus from a dictionary (eg. given by JSON or YAML).
        The bus type is loaded from the module key of the dictionary
        :param data: The dictionary describing the bus
        :return: module.Bus, where module is the module given in data['module']
        """
        data.update(kwargs)
        if 'module' not in data:
            raise KeyError('To create a generic logger.Bus you need to provide the module')
        modname = data.pop('module')
        try:
            module = importlib.import_module(modname)
        except Exception:
            raise ValueError('Module "{}" not found, check configuration'.format(modname))
        else:
            for name, obj in vars(module).items():
                if isinstance(obj, type) and issubclass(obj, cls):
                    logger.debug(f'Found Bus:{obj.__name__}')
                    return obj(**data)
            raise KeyError('Module "{}" exists, but has no Bus class'.format(modname))

    @classmethod
    def from_file(cls, busfile, **kwargs):
        """
        Loads a Bus from a description file
        :param busfile: Filename of the yaml description of the bus
        :return: the bus
        """
        data = yaml.safe_load(busfile)
        data.update(kwargs)
        return cls.from_dict(data)

    def to_file(self, busfile):
        """
        Saves the current bus description as a yaml file
        :param busfile: Filename to save. For further use, the file should match to: preferences/*.bus.yaml
        """
        self.to_stream(open(busfile, 'w'))

    def to_stream(self, stream):
        yaml.safe_dump(
            self.__asdict__(),
            stream,
            default_flow_style=False,
            sort_keys=False,
        )


__OpenTypes = typing.Optional[typing.Union[typing.Mapping, typing.IO, str]]


def open_bus(source: __OpenTypes = None, **kwargs) -> Bus:
    """
    Loads a Bus from a dict, a stream or a filename
    :param source: Either a dict, a file stream, a filename or a string containing a yaml-document
    :return: The created Bus
    """
    import os
    if isinstance(source, typing.Mapping):
        return Bus.from_dict(source, **kwargs)
    elif isinstance(source, typing.IO):
        return Bus.from_file(source, **kwargs)
    elif isinstance(source, str) and os.path.exists(source):
        with open(source) as f:
            return Bus.from_file(f, **kwargs)
    elif isinstance(source, str):
        try:
            d = yaml.safe_load(source)
        except:
            raise BusError(f'open_bus: Source does not contain a Bus-Description: {source}')
        else:
            return Bus.from_dict(d, **kwargs)
    elif source is None:
        return Bus.from_dict(kwargs)
    else:
        raise BusError(f'open_bus: Cannot handle source: {source}')
