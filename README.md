PyLoopEnergy
======

This provides a python API to [Loop Energy](https://www.your-loop.com) who provide electricity and gas monitors.

It uses their service to provide readings that are updated every 10 seconds for electricity, and every 15 minutes for gas.

To use the service you need the the client serial number and secret keys for your devices.

You can get this by logging into your-loop.com, opening your browser's console, and typing in ```Drupal.settings.navetas_realtime```.

(There is more detailed documentation about how to do this here https://home-assistant.io/components/sensor.loop_energy/)

*You should keep your secret keys,* **secret!**

Thanks to Marcos Scriven for producing a node implementation that I've shamelessly copied. https://github.com/marcosscriven/loop

Data is returned in kw.

Dependencies
------------
PyLoopEnergy depends on socketIO-client. It needs version 0.5.6 which supports socket.IO version 0.9, rather than 1.0.


How to use
----------

    >> import pyloopenergy
    >> elec_serial = 'your serial'
    >> elec_secret = 'your_secret'
    >> le = pyloopenergy.LoopEnergy(elec_serial, elec_secret)
    >> le.electricity_useage

    0.602

    >> le.terminate()

Notes:
 1. Data is fetched asynchronously, so `le` may not be populated if you call `electricity_useage` straight after creating it. The API provides callback functions on update (there is a simple example below).
 2. It can take 15s to terminate the monitoring thread after calling `terminate`.


Simple subscription example
---------
````
import pyloopenergy
import time

def gas_trace():
    print("Gas =", le.gas_useage)

def elec_trace():
    print("Electricity =", le.electricity_useage)

elec_serial = '00000';
elec_secret = 'YYYYYY';

gas_serial = '11111';
gas_secret = 'ZZZZZ';

le = pyloopenergy.LoopEnergy(elec_serial, elec_secret, gas_serial, gas_secret)
le.subscribe_gas(gas_trace)
le.subscribe_elecricity(elec_trace)

time.sleep(120)
le.terminate()
time.sleep(60)
````
This produces the following output.

````
Electricity = 1.13
Gas = 0.0
Electricity = 1.116
````

Gas Meter Types and Calorific values
---------

The library supports metric and imperial gas meters (reading cubic metres or 100s of cubic feet)

The default is a metric meter, but you can specify an imperial or metric meter.

````
le = pyloopenergy.LoopEnergy(elec_serial, elec_secret, gas_serial, gas_secret, pyloopenergy.IMPERIAL)

le = pyloopenergy.LoopEnergy(elec_serial, elec_secret, gas_serial, gas_secret, pyloopenergy.METRIC)

````

To convert from a volume reading into kw, the library needs to know how much energy is in each metre of gas. The default is 39.11, but you can use the real number from your supplier if you like.

````
le = pyloopenergy.LoopEnergy(elec_serial, elec_secret, gas_serial, gas_secret, pyloopenergy.IMPERIAL, 39.1)

le = pyloopenergy.LoopEnergy(elec_serial, elec_secret, gas_serial, gas_secret, pyloopenergy.METRIC, 39.1)

````


