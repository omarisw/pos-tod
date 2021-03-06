# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple
import logging
import re
import serial
import threading
import time

from odoo.addons.hw_drivers.iot_handlers.drivers.SerialBaseDriver import SerialDriver, SerialProtocol, serial_connection
from odoo.addons.hw_drivers.iot_handlers.drivers.SerialScaleDriver import ScaleDriver

_logger = logging.getLogger(__name__)

# Only needed to ensure compatibility with older versions of Odoo
ACTIVE_SCALE = None
new_weight_event = threading.Event()

ScaleProtocol = namedtuple('ScaleProtocol', SerialProtocol._fields + ('zeroCommand', 'tareCommand', 'clearCommand', 'autoResetWeight'))
TorreyProtocol = ScaleProtocol(
    name='Torrey SR-50',
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    stopbits=serial.STOPBITS_ONE,
    parity=serial.PARITY_NONE,
    timeout=1,
    writeTimeout=1,
    measureRegexp=b'\s*([0-9.]+)\s',
    statusRegexp=None,
    commandDelay=0.2,
    measureDelay=0.5,
    newMeasureDelay=0.2,
    commandTerminator=b"\r\n",
    measureCommand=b'P',
    zeroCommand=b'Z',
    tareCommand=b'T',
    clearCommand=b'C',
    emptyAnswerValid=False,
    autoResetWeight=False,
)
#end added protocol

# Ensures compatibility with older versions of Odoo
# class ScaleReadOldRoute(http.Controller):
#     @http.route('/hw_proxy/scale_read', type='json', auth='none', cors='*')
#     def scale_read(self):
#         if ACTIVE_SCALE:
#             return {'weight': ACTIVE_SCALE._scale_read_old_route()}
#         return None


# class ScaleDriver(SerialDriver):
#     """Abstract base class for scale drivers."""
#     last_sent_value = None
#
#     def __init__(self, identifier, device):
#         super(ScaleDriver, self).__init__(identifier, device)
#         self.device_type = 'scale'
#         self._set_actions()
#         self._is_reading = True
#
#         # Ensures compatibility with older versions of Odoo
#         # Only the last scale connected is kept
#         global ACTIVE_SCALE
#         ACTIVE_SCALE = self
#         proxy_drivers['scale'] = ACTIVE_SCALE
#
#     # Ensures compatibility with older versions of Odoo
#     # and allows using the `ProxyDevice` in the point of sale to retrieve the status
#     def get_status(self):
#         """Allows `hw_proxy.Proxy` to retrieve the status of the scales"""
#
#         status = self._status
#         return {'status': status['status'], 'messages': [status['message_title'], ]}
#
#     def _set_actions(self):
#         """Initializes `self._actions`, a map of action keys sent by the frontend to backend action methods."""
#
#         self._actions.update({
#             'read_once': self._read_once_action,
#             'set_zero': self._set_zero_action,
#             'set_tare': self._set_tare_action,
#             'clear_tare': self._clear_tare_action,
#             'start_reading': self._start_reading_action,
#             'stop_reading': self._stop_reading_action,
#         })
#
#     def _start_reading_action(self, data):
#         """Starts asking for the scale value."""
#         self._is_reading = True
#
#     def _stop_reading_action(self, data):
#         """Stops asking for the scale value."""
#         self._is_reading = False
#
#     def _clear_tare_action(self, data):
#         """Clears the scale current tare weight."""
#
#         # if the protocol has no clear tare command, we can just tare again
#         clearCommand = self._protocol.clearCommand or self._protocol.tareCommand
#         self._connection.write(clearCommand + self._protocol.commandTerminator)
#
#     def _read_once_action(self, data):
#         """Reads the scale current weight value and pushes it to the frontend."""
#
#         self._read_weight()
#         self.last_sent_value = self.data['value']
#         event_manager.device_changed(self)
#
#     def _set_zero_action(self, data):
#         """Makes the weight currently applied to the scale the new zero."""
#
#         self._connection.write(self._protocol.zeroCommand + self._protocol.commandTerminator)
#
#     def _set_tare_action(self, data):
#         """Sets the scale's current weight value as tare weight."""
#
#         self._connection.write(self._protocol.tareCommand + self._protocol.commandTerminator)
#
#     @staticmethod
#     def _get_raw_response(connection):
#         """Gets raw bytes containing the updated value of the device.
#
#         :param connection: a connection to the device's serial port
#         :type connection: pyserial.Serial
#         :return: the raw response to a weight request
#         :rtype: str
#         """
#
#         answer = []
#         while True:
#             char = connection.read(1)
#             if not char:
#                 break
#             else:
#                 answer.append(bytes(char))
#         return b''.join(answer)
#
#     def _read_weight(self):
#         """Asks for a new weight from the scale, checks if it is valid and, if it is, makes it the current value."""
#
#         protocol = self._protocol
#         self._connection.write(protocol.measureCommand + protocol.commandTerminator)
#         answer = self._get_raw_response(self._connection)
#         match = re.search(self._protocol.measureRegexp, answer)
#         if match:
#             self.data = {
#                 'value': float(match.group(1)),
#                 'status': self._status
#             }
#
#     # Ensures compatibility with older versions of Odoo
#     def _scale_read_old_route(self):
#         """Used when the iot app is not installed"""
#         with self._device_lock:
#             self._read_weight()
#         return self.data['value']
#
#     def _take_measure(self):
#         """Reads the device's weight value, and pushes that value to the frontend."""
#
#         with self._device_lock:
#             self._read_weight()
#             if self.data['value'] != self.last_sent_value or self._status['status'] == self.STATUS_ERROR:
#                 self.last_sent_value = self.data['value']
#                 event_manager.device_changed(self)
#added class
class TorreyDriver(ScaleDriver):
    """Driver for the Toldedo 8217 serial scale."""
    _protocol = TorreyProtocol

    def __init__(self, identifier, device):
        super(TorreyDriver, self).__init__(identifier, device)
        self.device_manufacturer = 'Torrey'

    @classmethod
    def supported(cls, device):
        """Checks whether the device, which port info is passed as argument, is supported by the driver.

        :param device: path to the device
        :type device: str
        :return: whether the device is supported by the driver
        :rtype: bool
        """

        protocol = cls._protocol

        try:
            with serial_connection(device['identifier'], protocol, is_probing=True) as connection:
                connection.write(b'Ehello' + protocol.commandTerminator)
                time.sleep(protocol.commandDelay)
                answer = connection.read(8)
                if answer == b'\x02E\rhello':
                    connection.write(b'F' + protocol.commandTerminator)
                    return True
        except serial.serialutil.SerialTimeoutException:
            pass
        except Exception:
            _logger.exception('Error while probing %s with protocol %s' % (device, protocol.name))
        return False
    
    # Ensures compatibility with older versions of Odoo
    def _scale_read_old_route(self):
        """Used when the iot app is not installed"""

        time.sleep(3)
        with self._device_lock:
            self._read_weight()
            self._check_last_weight_time()
        return self.data['value']
#end added class