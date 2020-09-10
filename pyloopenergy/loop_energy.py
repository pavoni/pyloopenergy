#!/usr/bin/env python
# encoding: utf-8

"""
Python interface to talk to loop energy electricity
and gas monitors (https://www.your-loop.com/)
"""

import threading
import logging
import time
import requests
import socketio

SIO = socketio.Client()

LOG = logging.getLogger(__name__)

LOOP_SERVER = 'https://www.your-loop.com:443'

# How long to wait for updates before assuming the connection
# has died (and so reconnect) (secs)
RECONNECT_AFTER = 60

# Time to wait for updates (secs)
WAIT_BEFORE_POLL = 15

# Time to wait for updates (secs)
WAIT_BEFORE_RETRY = 60

# https://www.gov.uk/guidance/gas-meter-readings-and-bill-calculation
# Energy value of the gas in MJ per m3
DEFAULT_CALORIFIC = 39.11
# Correction factor to ref temp and pressure
VOLUME_CORRECTION = 1.02264
# 100 cu ft to m3 conversion factor
METRIC_CONVERSION = 2.83

# Meter types
METRIC = 'metric'
IMPERIAL = 'imperial'


class LoopEnergy():
    # pylint: disable=too-many-instance-attributes
    """
    Python interface to talk to loop energy electricity
    and gas monitors (https://www.your-loop.com/)
    Based on reverse engineering by marcosscriven
    https://github.com/marcosscriven/loop
    """

    def __init__(self, elec_serial, elec_secret,
                 gas_serial=None, gas_secret=None,
                 gas_meter_type=METRIC, gas_calorific=DEFAULT_CALORIFIC):
        # pylint: disable=too-many-arguments
        """
        Electricity is always required, gas is optional
        """
        self.elec_serial = elec_serial
        self.elec_secret = elec_secret

        self.gas_serial = gas_serial
        self.gas_secret = gas_secret
        self.gas_meter_type = gas_meter_type
        self.gas_meter_calorific = gas_calorific

        self.gas_reading = None
        self.gas_device_timestamp = None

        self.gas_kw = None
        self.elec_kw = None

        self.gas_rssi_value = None
        self.elec_rssi_value = None

        self.gas_old_timestamp = None
        self.gas_old_reading = None

        self._elec_callback = None
        self._gas_callback = None

        self.connected_ok = False
        self.thread_exit = False
        self.updated_in_interval = False
        self.reconnect_needed = False
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

    @property
    def gas_rssi(self):
        """RSSI from the gas meter device"""
        return self.gas_rssi_value

    @property
    def electricity_rssi(self):
        """RSSI from the electricity meter device"""
        return self.elec_rssi_value

    def subscribe_gas(self, callback):
        """Add a callback function for gas updates."""
        self._gas_callback = callback

    def subscribe_elecricity(self, callback):
        """Add a callback function for electricity updates."""
        self._elec_callback = callback

    def _run_event_thread(self):

        @SIO.event
        def electric_realtime(data):  # pylint: disable=unused-variable
            self._update_elec(data)

        @SIO.event
        def gas_interval(data):  # pylint: disable=unused-variable
            self._update_gas(data)

        @SIO.event
        def disconnect():  # pylint: disable=unused-variable
            LOG.debug('Socket disconnected')

        @SIO.event
        def connect():  # pylint: disable=unused-variable
            LOG.debug('Socket connected')

        @SIO.event
        def connect_error(err):  # pylint: disable=unused-variable
            LOG.debug('Socket connection failed (%s)', err)

        LOG.info('Started LoopEnergy thread')

        while not self.thread_exit:
            try:
                if self.reconnect_needed:
                    LOG.warning('Waiting %ds to retry socket connection', WAIT_BEFORE_RETRY)
                    SIO.disconnect()
                    SIO.sleep(WAIT_BEFORE_RETRY)
                    LOG.warning('Retrying socket connection')
                    SIO.connect(LOOP_SERVER)
                else:
                    LOG.info('Opening socket connection')
                    SIO.connect(LOOP_SERVER)
                self.reconnect_needed = False
                SIO.emit('subscribe_electric_realtime',
                         {
                             'serial': self.elec_serial,
                             'clientIp': '127.0.0.1',
                             'secret': self.elec_secret
                         })

                if self.gas_serial is not None:
                    SIO.emit('subscribe_gas_interval',
                             {
                                 'serial': self.gas_serial,
                                 'clientIp': '127.0.0.1',
                                 'secret': self.gas_secret
                             })
                intervals_without_update = 0
                while not (self.thread_exit or self.reconnect_needed):
                    self.updated_in_interval = False
                    SIO.sleep(WAIT_BEFORE_POLL)
                    if self.updated_in_interval:
                        intervals_without_update = 0
                    else:
                        intervals_without_update += 1
                    time_without_update = (
                        intervals_without_update * WAIT_BEFORE_POLL)
                    if time_without_update > RECONNECT_AFTER:
                        self.reconnect_needed = True
                        LOG.warning('No updates for %ss - reconnecting',
                                    RECONNECT_AFTER)
                    LOG.debug('LoopEnergy thread poll')
            except (
                    ValueError,
                    AttributeError,
                    IndexError,
                    requests.exceptions.RequestException,
                    socketio.exceptions.ConnectionError
                ) as ex:
                # Looks like ValueError comes from an
                # invalid HTTP packet return
                # Looks like AttributeError comes from a
                # failed SSL connection
                LOG.warning('Exception (will try to reconnect) -  %s', ex)
                self.reconnect_needed = True
        LOG.info('Exiting LoopEnergy thread')
        SIO.disconnect()

    def _update_elec(self, arg):
        self.connected_ok = True
        self.updated_in_interval = True
        self.elec_kw = arg['inst'] / 1000.0
        self.elec_rssi_value = arg['rssi']
        LOG.info('Electricity rate: %s', self.elec_kw)
        if self._elec_callback is not None:
            self._elec_callback()

    def _update_gas(self, arg):
        # DeviceTimestamp is the time (in secs) when the reading was taken
        # totalRegister looks to be related to the meter reading

        self.connected_ok = True
        self.updated_in_interval = True
        gas_reading = arg['totalRegister']
        gas_rssi = arg['rssi']
        device_timestamp = arg['deviceTimestamp']
        if device_timestamp == self.gas_device_timestamp:
            # we have this already
            return

        self.gas_old_timestamp = self.gas_device_timestamp
        self.gas_device_timestamp = device_timestamp

        self.gas_old_reading = self.gas_reading
        self.gas_reading = gas_reading
        self.gas_rssi_value = gas_rssi

        if self.gas_old_timestamp is None:
            return
        if self.gas_old_reading is None:
            return
        gas_used = (self.gas_reading - self.gas_old_reading)
        secs = float(self.gas_device_timestamp - self.gas_old_timestamp)
        hours = secs / (60 * 60)
        self.gas_kw = self._convert_kw(gas_used, hours)
        LOG.info('Gas rate: %s', self.gas_kw)
        if self._gas_callback is not None:
            self._gas_callback()

    def _convert_kw(self, gas_used, period):
        """
        Convert gas reading to kw
        For details see
        https://www.gov.uk/guidance/gas-meter-readings-and-bill-calculation
        """
        if self.gas_meter_type == METRIC:
            cu_metres = gas_used
        elif self.gas_meter_type == IMPERIAL:
            cu_metres = gas_used * METRIC_CONVERSION
        else:
            cu_metres = 0
            LOG.error('Unsupported meter type %s', self.gas_meter_type)

        m_joules = cu_metres * self.gas_meter_calorific * VOLUME_CORRECTION
        kwh = m_joules / 3600
        return kwh / period

    def terminate(self):
        """
        Close down the update thread
        """
        LOG.info('Terminate thread')
        SIO.disconnect()
        self.thread_exit = True
        self._event_thread.join()
