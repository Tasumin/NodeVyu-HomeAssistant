# NodeVyu Home Assistant

Official Home Assistant custom integration for [NodeVyu](https://nodevyu.com).

## Current capabilities

- UI-based config flow
- Location-scoped NodeVyu integration tokens
- NodeVyu device and agent discovery
- Agent connectivity binary sensors
- Device connectivity binary sensors
- Agent version sensors
- Real-time NodeVyu event stream over Server-Sent Events
- Fires Home Assistant `nodevyu_event` events for NodeVyu integration events
- Automatic stream reconnect and periodic status refresh

## Install for development

Copy `custom_components/nodevyu` into the Home Assistant configuration directory:

```text
/config/custom_components/nodevyu
```

For a Docker installation where `/opt/homeassistant/config` is mounted as `/config`, the host path is:

```text
/opt/homeassistant/config/custom_components/nodevyu
```

Restart Home Assistant, then go to **Settings → Devices & services → Add integration → NodeVyu**.

Enter:

- **NodeVyu URL:** `https://nodevyu.com`
- **Integration token:** the `nv_ha_...` token generated from the NodeVyu location's Integrations section.

## Architecture

Each Home Assistant config entry represents one NodeVyu location. Tokens are scoped by NodeVyu to that location. Multiple NodeVyu locations can therefore connect to the same Home Assistant instance independently, and different locations can connect to different Home Assistant instances.

NodeVyu remains the source of truth for monitoring. Home Assistant receives current state through the status API and real-time transitions through the NodeVyu SSE integration stream.

## Status

Early development release (`0.1.0`). The NodeVyu server-side Home Assistant API must be deployed before this integration can connect.
