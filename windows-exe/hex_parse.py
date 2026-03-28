import json

def parse_int24(byte_data, is_signed=False):
    val = (byte_data[0] << 16) | (byte_data[1] << 8) | byte_data[2]
    if is_signed and (val & 0x800000):
        val -= 0x1000000
    return val

def decode_lora(hex_string):
    clean_hex = hex_string.replace(" ", "").upper()
    
    try:
        data = bytes.fromhex(clean_hex)
    except ValueError:
        return {"error": "Invalid hex string"}

    if len(data) < 5:
        return {"error": "Hex string too short to contain required fields"}

    msg_type_raw = data[3]
    if msg_type_raw == 0x01:
        msg_type_str = "data_report"
    elif msg_type_raw == 0x02:
        msg_type_str = "heartbeat"
    elif msg_type_raw == 0xFF:
        msg_type_str = "error"
    else:
        msg_type_str = "unknown"

    packet = {
        "version": data[0],
        "lab_id": data[1],
        "node_id": data[2],
        "msg_type": msg_type_str,
        "channel_count": data[4],
        "channels": []
    }

    current_idx = 5
    for _ in range(packet["channel_count"]):
        if current_idx + 4 > len(data):
            packet["error"] = "Not enough data for all channels"
            break
            
        channel_type = data[current_idx]
        raw_val_bytes = data[current_idx + 1:current_idx + 4]
        
        channel_data = {"channel_type": channel_type}

        if channel_type == 0x01:
            raw_int = parse_int24(raw_val_bytes, is_signed=True)
            channel_data["value"] = raw_int / 100.0
            channel_data["metric"] = "temperature_celsius"
        elif channel_type == 0x02:
            channel_data["value"] = parse_int24(raw_val_bytes) == 1
            channel_data["metric"] = "door_open"
        elif channel_type == 0x03:
            channel_data["value"] = parse_int24(raw_val_bytes, is_signed=False)
            channel_data["metric"] = "light_adc"
        elif channel_type == 0x04:
            channel_data["value"] = parse_int24(raw_val_bytes) == 1
            channel_data["metric"] = "doorbell_rung"
        elif channel_type == 0x05:
            channel_data["value"] = parse_int24(raw_val_bytes, is_signed=False) == 1
            channel_data["metric"] = "power_drawing"
        elif channel_type == 0x06:
            channel_data["value"] = parse_int24(raw_val_bytes, is_signed=False)
            channel_data["metric"] = "current_milliamps"
        else:
            channel_data["value"] = parse_int24(raw_val_bytes)
            channel_data["metric"] = "unknown"

        packet["channels"].append(channel_data)
        current_idx += 4

    return packet

if __name__ == "__main__":
    raw_input = "01 01 01 01 02 01 00 01 C5 02 00 00 00"
    decoded_data = decode_lora(raw_input)
    print(json.dumps(decoded_data, indent=2))
    with open('test.json', 'w') as f:
        json.dump(decoded_data, f, indent=4)