# packet.py
# Biodesign Center IoT Network — LoRa packet encoding
# Protocol version 1
#
# Keep this file identical between transmitter/ and receiver/.
# If you add a new channel type here, add it in both copies.

PROTOCOL_VERSION = 0x01

# msg_type values
MSG_DATA  = 0x01
MSG_ERROR = 0xFF

# channel_type codes
CH_TEMPERATURE  = 0x01
CH_DOOR         = 0x02
CH_LIGHT_LEVEL  = 0x03
CH_LIGHT_EVENT  = 0x04
CH_CURRENT_DRAW = 0x05
CH_CURRENT_AMPS = 0x06

# Lookup tables for encode/decode
_CHANNEL_NAMES = {
    CH_TEMPERATURE:  "temperature",
    CH_DOOR:         "door",
    CH_LIGHT_LEVEL:  "light_level",
    CH_LIGHT_EVENT:  "light_event",
    CH_CURRENT_DRAW: "current_draw",
    CH_CURRENT_AMPS: "current_amps",
}
_CHANNEL_CODES = {v: k for k, v in _CHANNEL_NAMES.items()}


# --- Internal helpers ---

def _pack_int24_be(value):
    """Signed 24-bit integer -> 3 big-endian bytes (two's complement)."""
    if value < 0:
        value = value & 0xFFFFFF
    return bytes([(value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])


def _unpack_int24_be(b):
    """3 big-endian bytes -> signed 24-bit integer."""
    val = (b[0] << 16) | (b[1] << 8) | b[2]
    if val & 0x800000:
        val -= 0x1000000
    return val


def _unpack_uint24_be(b):
    """3 big-endian bytes -> unsigned 24-bit integer."""
    return (b[0] << 16) | (b[1] << 8) | b[2]


# --- Public API ---

def encode_channel(channel_name, value):
    """
    Encode one channel block (4 bytes: 1 type byte + 3 value bytes).

    Value semantics per channel type:
      temperature  : float, degrees Celsius  (stored as int * 100)
      door         : bool, False=closed True=open
      light_level  : int, raw ADC count
      light_event  : bool, True=ring detected
      current_draw : bool, True=drawing power
      current_amps : int, milliamps

    Raises ValueError for unknown channel names.
    """
    code = _CHANNEL_CODES.get(channel_name)
    if code is None:
        raise ValueError("Unknown channel: {}".format(channel_name))

    if channel_name == "temperature":
        raw = int(round(value * 100))
        return bytes([code]) + _pack_int24_be(raw)
    elif channel_name in ("door", "light_event", "current_draw"):
        return bytes([code, 0x00, 0x00, 0x01 if value else 0x00])
    elif channel_name in ("light_level", "current_amps"):
        return bytes([code]) + _pack_int24_be(int(value))
    else:
        raise ValueError("Unhandled channel: {}".format(channel_name))


def encode_packet(lab_id, node_id, msg_type, channels=None):
    """
    Build a complete packet.

    channels: list of (channel_name, value) tuples, or None/[] for heartbeat.
    Returns bytearray.

    Example — data packet with temp=4.53 and door=closed:
      encode_packet(1, 1, MSG_DATA, [("temperature", 4.53), ("door", False)])
      -> bytearray b'\\x01\\x01\\x01\\x01\\x02\\x01\\x00\\x01\\xc5\\x02\\x00\\x00\\x00'

    """
    channels = channels or []
    header = bytearray([
        PROTOCOL_VERSION,
        lab_id,
        node_id,
        msg_type,
        len(channels),
    ])
    body = bytearray()
    for ch_name, ch_val in channels:
        body += encode_channel(ch_name, ch_val)
    return header + body


def decode_packet(data):
    """
    Decode a received packet.

    Returns dict:
      version   : int
      lab_id    : int
      node_id   : int
      msg_type  : int
      channels  : list of (channel_name, decoded_value)

    Raises ValueError on malformed input.
    """
    if len(data) < 5:
        raise ValueError("Packet too short ({} bytes)".format(len(data)))

    version   = data[0]
    lab_id    = data[1]
    node_id   = data[2]
    msg_type  = data[3]
    ch_count  = data[4]

    expected_len = 5 + ch_count * 4
    if len(data) < expected_len:
        raise ValueError(
            "Expected {} bytes for {} channels, got {}".format(
                expected_len, ch_count, len(data)
            )
        )

    channels = []
    offset = 5
    for _ in range(ch_count):
        ch_code  = data[offset]
        ch_bytes = data[offset + 1:offset + 4]
        ch_name  = _CHANNEL_NAMES.get(ch_code, "unknown_0x{:02x}".format(ch_code))

        if ch_name == "temperature":
            value = _unpack_int24_be(ch_bytes) / 100.0
        elif ch_name in ("door", "light_event", "current_draw"):
            value = bool(ch_bytes[2])
        elif ch_name in ("light_level", "current_amps"):
            value = _unpack_uint24_be(ch_bytes)
        else:
            value = _unpack_uint24_be(ch_bytes)  # raw fallback for unknown types

        channels.append((ch_name, value))
        offset += 4

    return {
        "version":   version,
        "lab_id":    lab_id,
        "node_id":   node_id,
        "msg_type":  msg_type,
        "channels":  channels,
    }
