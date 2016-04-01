#!/usr/bin/env python
# encoding: utf-8

"""
Python interface to talk to loop energy electricity
and gas monitors (https://www.your-loop.com/)
"""

import threading

import logging

# Uses Socket.io protocol 0.9 - so is not compatible with 1.0
# So important to use socketIO-client v 0.5.6
import socketIO_client

LOG = logging.getLogger(__name__)

LOOP_SERVER = 'https://www.your-loop.com'
LOOP_PORT = 443

# M3 x Calorific value 39.4 x volume correction 1.02264 / 3.6 = 11.1922
# This figure to matches loop energy's dashboard
CONVERSION_FACTOR = 11.11


class LoopEnergy():
    # pylint: disable=too-many-instance-attributes
    """
    Python interface to talk to loop energy electricity
    and gas monitors (https://www.your-loop.com/)
    Based on reverse engineering by marcosscriven
    https://github.com/marcosscriven/loop
    """
    def __init__(self, elec_serial, elec_secret,
                 gas_serial=None, gas_secret=None):
        # pylint: disable=too-many-arguments
        '''
        Electricity is always required, gas is optional
        '''

        self.elec_serial = elec_serial
        self.elec_secret = elec_secret

        self.gas_serial = gas_serial
        self.gas_secret = gas_secret

        self.gas_reading = None
        self.gas_device_timestamp = None

        self.gas_kw = None
        self.elec_kw = None

        self.gas_old_timestamp = None
        self.gas_old_reading = None

        self._elec_callback = None
        self._gas_callback = None

        self.connected_ok = False
        self.thread_exit = False
        self._event_thread = threading.Thread(target=self._run_event_thread,
                                              name='LoopEnergy Event Thread')
        self._event_thread.start()

    @property
    def gas_useage(self):
        """instant gas useage."""
        return self.gas_kw

    @property
    def electricity_useage(self):
        """instant electricity useage."""
        return self.elec_kw

    @property
    def init_ok(self):
        """Were we able to connect?."""
        return self.connected_ok

    def subscribe_gas(self, callback):
        """Add a callback function for gas updates."""
        self._gas_callback = callback

    def subscribe_elecricity(self, callback):
        """Add a callback function for electricity updates."""
        self._elec_callback = callback

    def _run_event_thread(self):

        class Namespace(socketIO_client.BaseNamespace):
            """Class top allow socket_io error callbacks."""

            def on_disconnect(inner_self):
                # pylint: disable=no-self-argument
                if self.thread_exit:
                    return
                if self.connected_ok:
                    LOG.warning(
                        'Disconnected from https://www.your-loop.com, '
                        'will retry')
                    return

                LOG.error('Could not connect to https://www.your-loop.com')
                LOG.error('Please check your keys are correct. Terminating')
                self.terminate()

        LOG.info('Started LoopEnergy thread')
        while not self.thread_exit:
            LOG.debug('Opening socket connection')
            with socketIO_client.SocketIO(
                    LOOP_SERVER, LOOP_PORT,
                    Namespace) as socket_io:
                socket_io.on('electric_realtime', self._update_elec)
                socket_io.on('gas_interval', self._update_gas)
                socket_io.emit('subscribe_electric_realtime',
                               {
                                   'serial': self.elec_serial,
                                   'clientIp': '127.0.0.1',
                                   'secret': self.elec_secret
                               })

                if self.gas_serial is not None:
                    socket_io.emit('subscribe_gas_interval',
                                   {
                                       'serial': self.gas_serial,
                                       'clientIp': '127.0.0.1',
                                       'secret': self.gas_secret
                                   })
                while not self.thread_exit:
                    socket_io.wait(seconds=15)
                    LOG.debug('LoopEnergy thread poll')
        LOG.info('Exiting LoopEnergy thread')

    def _update_elec(self, arg):
        self.connected_ok = True
        self.elec_kw = arg['inst']/1000.0
        LOG.info('Electricity rate: %s', self.elec_kw)
        if self._elec_callback is not None:
            self._elec_callback()

    def _update_gas(self, arg):
        # These details aren't documented
        # Data returned is:-
        # 'statusByte2': 1,
        # 'statusByte3': 16,
        # 'receivedTimestamp': 1459348277,
        # 'totalRegister': 12820,
        # 'serial': '[removed]',
        # 'deviceTimestamp': 1459348200,
        # 'lqi': 47,
        # 'rssi': -66,
        # 'lux': 1}

        # DeviceTimestamp is the time (in secs) when the reading was taken
        # totalRegister looks to be related to the meter reading
        # My meter is m3 - suspect this is defined by the statusBytes!

        self.connected_ok = True
        gas_reading = arg['totalRegister']
        device_timestamp = arg['deviceTimestamp']
        if device_timestamp == self.gas_device_timestamp:
            # we have this already
            return

        self.gas_old_timestamp = self.gas_device_timestamp
        self.gas_device_timestamp = device_timestamp

        self.gas_old_reading = self.gas_reading
        self.gas_reading = gas_reading

        if self.gas_old_timestamp is None:
            return
        if self.gas_old_reading is None:
            return
        gas_used = (self.gas_reading - self.gas_old_reading)
        period = (self.gas_device_timestamp - self.gas_old_timestamp)/(60*60)
        self.gas_kw = (CONVERSION_FACTOR * gas_used / period)/1000
        LOG.info('Gas rate: %s', self.gas_kw)
        if self._gas_callback is not None:
            self._gas_callback()

    def terminate(self):
        '''
        Close down the update thread
        '''
        LOG.info('Terminate thread')
        self.thread_exit = True
        self._event_thread.join()
