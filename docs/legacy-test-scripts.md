# Legacy Test Scripts

## Overview

`transmitter.py` and `receiver.py` in the repo root are the original PING/PONG LoRa connectivity test scripts. They predate the packet protocol and are not part of the current system.

## `transmitter.py`

Sends a `"PING N"` string every 30 seconds over LoRa, then listens 5 seconds for a `"PONG"` reply. Flashes LED twice on successful round-trip.

## `receiver.py`

Listens for incoming packets, prints the ASCII contents and RSSI, then replies with `"PONG N"`.

## Purpose

Used to verify basic LoRa radio communication between two Feather RP2040 boards before the binary packet protocol was designed.
