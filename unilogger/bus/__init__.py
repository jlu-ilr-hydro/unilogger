"""
The Bus-System
--------------

Busses are ways for the unilogger to communicate with measurement devices. A Bus can be understood as
a wrapper of the device specific protocol to an universal API. The concrete instance of a bus
is defined with a yaml file - the layout of parameters is heavily depending on the Bus implementation.

In most cases, multiple sensors can be attached to a Bus: Eg. for the SDI12-Bus, a couple of sensors at
different addresses are connected. Each of the sensor can produce multiple values.

But the sensor level is not necessary - in essence a Bus a protocol, that can produce, when read multiple values
with proper meta data.

The general layout of a Bus is:

- Bus -> has multiple Sensors
- Sensor -> has ValueFactorys (see :py:class:`unilogger.bus.base.ValueFactory`)

Every Bus must implement the following methods:

- **__asdict__**: Returns a dictionary that describes a bus with every attached sensor and measured values
- **read_all** (coroutine): Reads all values defined for the bus and returns a list of Values (see: :py:class:`unilogger.bus.Value`)
- **__init__**: The Init function must accept all key words from the defining yaml file

The open_bus function loads the bus description (usally from a yaml file
"""

from .base import open_bus, Value
