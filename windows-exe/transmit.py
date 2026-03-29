# SPDX-License-Identifier: MIT

# Example to send a packet periodically
# Author: Jerry Needell
#
import time

import board
import busio
import digitalio

import adafruit_rfm9x
def send_packet(transmit_interval, radio_freq_mhz=915.0, tx_power=23):
    # set the time interval (seconds) for sending packets
    # Define radio parameters.
    # module! Can be a value like 915.0, 433.0, etc.

    # Define pins connected to the chip.    
    CS = digitalio.DigitalInOut(board.CE1)
    RESET = digitalio.DigitalInOut(board.D25)

    # Initialize SPI bus.
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    # Initialze RFM radio
    rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, radio_freq_mhz)

    # Note that the radio is configured in LoRa mode so you can't control sync
    # word, encryption, frequency deviation, or other settings!

    # You can however adjust the transmit power (in dB).  The default is 13 dB but
    # high power radios like the RFM95 can go up to 23 dB:
    rfm9x.tx_power = tx_power


    # initialize counter
    counter = 0
    # send a broadcast mesage
    rfm9x.send(bytes(f"message number {counter}", "UTF-8"))
    print(f"Sent message number {counter}")
    counter += 1