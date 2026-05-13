# boot.py — runs once at startup, before code.py
# Biodesign Center IoT Network
#
# Bound the USB CDC console write timeout so print() cannot block the main
# loop indefinitely if the host-side CDC endpoint stalls. Without this, a
# stalled console would park code.py inside a print() call, defeating both
# the try/except fault handler and the host's silence warning.
import usb_cdc

if usb_cdc.console is not None:
    usb_cdc.console.write_timeout = 0.5
