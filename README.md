PyLoopEnergy
======

This provides a python API to [Loop Energy](https://www.your-loop.com) who provide electricity and monitors.

It uses their service to provide readings that are updated every 10 seconds for electrricity, and the gas every 15 minutes.

To use the service you need the the client serial number and secret keys for your devices.

You can get this by logging into your-loop.com, opening your browser's terminal, and typing in ```Drupal.settings.navetas_realtime```.

*You should keep your secret keys,* **secret!**

Thanks for Marcos Scriven for producing a node implementation that I've shamelessly copied! http://marcosscriven.github.io/loop/

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
 2. It can take 60s to terminate the monitoring thread after calling `terminte`.
