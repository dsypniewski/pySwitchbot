# pySwitchbot [![Build Status](https://travis-ci.org/Danielhiversen/pySwitchbot.svg?branch=master)](https://travis-ci.org/Danielhiversen/pySwitchbot)
Library to control Switchbot IoT devices https://www.switch-bot.com/bot

## Obtaining locks encryption key
Using the script `switchbot_get_lock_key.py` that's installed with this package you can manually obtain locks encryption key.

### CLI auth
```shell
switchbot_get_lock_key.py MAC USERNAME
```

Where `MAC` is MAC address of the lock and `USERNAME` is your SwitchBot account username, after that script will ask for your password.
If authentication succeeds then script should output your key id and encryption key.

### WEB auth
* This option allows to use Google, Apple etc. as authentication providers
* Works only on linux
* Tested on Ubuntu 22.04
```shell
switchbot_get_lock_key.py --web-auth MAC
```
Where `MAC` is MAC address of the lock. This option will create a custom url handler needed for retrieving the auth details, open a web UI where you can log in, and after that retrieve the key for the specified device.


[Buy me a coffee :)](http://paypal.me/dahoiv)
