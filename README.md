PyLoopEnergy
======

This provides a python API to [Loop Energy](https://www.your-loop.com) who provide electricity and monitors.

It uses their service to provide readings that are updated every 10 seconds for electricity, and the gas every 15 minutes.

To use the service you need the the client serial number and secret keys for your devices.

You can get this by logging into your-loop.com, opening your browser's terminal, and typing in ```Drupal.settings.navetas_realtime```.

*You should keep your secret keys,* **secret!**

Thanks for Marcos Scriven for producing a node implementation that I've shamelessly copied! https://github.com/marcosscriven/loop

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
 1. Data is fetched asynchronously, so `le` may not be populated if you `electricity_useage` straight after creating it. The API provides callback functions on update (add details here).
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

The gas code assumes that the meter is a metric meter - and I've added come comments on the info that I suspect specifies my meter type. Enhancements welcome for other meter types!
