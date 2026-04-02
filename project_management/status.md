# Biodesign Center IoT Network — Project Status

## Rules
- When adding to status, sort by severity and then difficulty. If either were not provided, make your best guess.
- 'Done' does not exist. When completing a task, delete it.

## Active Work

| Item | Status | Notes |
|------|--------|-------|
| — | — | — |

## Open Items

| Description | Severity | Difficulty |
|---|---|---|
| Collision detection and retry (CSMA-style backoff, ACK support, sequence numbers) | high | high |
| Refactor hardware code to have SENSORS be a list of all sensors (like temp, door) and other fields for the rest of the work (node_id should be unique to each transmitter) | medium | medium |
| Grafana should not receive sensor readings when sensors are down | medium | low |
| Over-the-air configuration or firmware update strategy | low | high |
| Remove all PERIODIC_SEND_INTERVAL references | low | low |
