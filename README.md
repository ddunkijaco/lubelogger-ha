# LubeLogger Home Assistant Integration

Home Assistant integration for [LubeLogger](https://github.com/hargata/lubelog), a web-based vehicle maintenance and fuel mileage tracker.

Fork of [hollowpnt92/lubelogger-ha](https://github.com/hollowpnt92/lubelogger-ha) that adds API-key authentication and write actions.

## Features

Creates a device for each vehicle in your LubeLogger instance with sensors for:

- Latest odometer reading
- Next planned maintenance item
- Latest tax payment
- Latest service record
- Latest repair record
- Latest upgrade record
- Latest supply/parts record
- Latest fuel fill-up
- Next reminder

Sensors only appear if data exists for that vehicle.

### Actions

| Action | Adds |
|---|---|
| `lubelogger.add_fuel_record` | A fuel fill-up (`odometer`, `fuel_consumed`, optional `cost`, `is_fill_to_full`, `missed_fuel_up`) |
| `lubelogger.add_odometer_record` | An odometer reading |
| `lubelogger.add_service_record` | A service record (`description`, `odometer`, optional `cost`) |
| `lubelogger.add_reminder` | A reminder due by `due_date`, `due_odometer`, or both |

All actions take a `vehicle_id` (the LubeLogger vehicle ID) and optional `date` (defaults to today), `notes` and `tags`. They return the created record as an action response.

```yaml
action: lubelogger.add_fuel_record
data:
  vehicle_id: 2
  odometer: "{{ states('sensor.odometer') | int }}"
  fuel_consumed: 11.4
```

## Installation

### HACS

1. Open HACS → ⋮ → Custom repositories
2. Add `https://github.com/ddunkijaco/lubelogger-ha` (Category: Integration)
3. Search for "LubeLogger" and install
4. Restart Home Assistant

### Manual

1. Copy `custom_components/lubelogger` to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration via Settings → Devices & Services

## Configuration

- **URL**: Your LubeLogger instance URL (e.g. `http://192.168.1.100:8080`)
- **API key** (recommended): create one in LubeLogger under Settings → API Keys. Use the **Editor** role if you want to use the actions; **Viewer** is enough for sensors only.
- **Username / Password**: used only when no API key is given (HTTP Basic auth).

Leave all credentials blank if LubeLogger authentication is disabled. Credentials can be changed later with **Reconfigure** on the integration.
