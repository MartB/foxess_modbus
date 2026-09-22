# FoxESS - Modbus

[![GitHub Release][releases-shield]][releases]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
[![Community Forum][forum-shield]][forum]

\*\* **This project is not endorsed by, directly affiliated with, maintained, authorized, or sponsored by FoxESS** \*\*

> ## This is a fork
>
> A fork of [nathanmarlor/foxess_modbus](https://github.com/nathanmarlor/foxess_modbus), which is the
> original and where the wiki and most of the documentation still live. Please raise issues with
> anything below [here](https://github.com/MartB/foxess_modbus/issues) rather than upstream.
>
> It keeps the `foxess_modbus` domain, so it replaces the original rather than sitting alongside it, and
> existing entities, config entries and dashboards carry on working. Uninstall the original first.
>
> Most of what it adds came out of running two H3s on firmware 1.93 as a parallel pair:
>
> - Talks Modbus through [tmodbus](https://github.com/wlcrs/tmodbus) rather than pymodbus. It is asyncio
>   throughout, which removed two workarounds for pymodbus's socket handling, and serial goes through
>   serialx, which Home Assistant ships.
> - No fixed gap between requests. The silence a serial line needs depends on its speed, and the layer
>   that knows the speed applies it; Modbus TCP needs none.
> - Read ranges are chosen by measured cost rather than by `max_read`, which is now just the largest read
>   the adapter will take. Raising it can no longer make polling slower.
> - Battery power on H3 1.93 comes from the battery's own voltage and current. The registers meant for it
>   read zero on a parallel slave and around 1.6x the real figure on a master.
> - The remote control cluster follows whichever inverter the parallel system made master, rather than
>   whichever was named in the options.
> - The battery, its BMSs and its modules appear as devices under the inverter.
> - More H3 sensors: BMS faults, per-module firmware and serials, the inverter's rated power, and whether
>   its clock has drifted.
>
> It needs Home Assistant 2026.3 or later, because the energy dashboard's grid source changed shape then.

## Introduction

A Home Assistant custom component which communicates with FoxESS H-series inverters and derivatives without using FoxESS's cloud.

This means that you're not reliant on FoxESS's cloud infrastructure, so HA keeps working when the cloud goes down.
You can also read solar production etc in real-time, rather than once every 5 minutes.

Depending on your inverter model, you can also set charge periods, work mode, min/max SoC.
See [Supported Features](https://github.com/nathanmarlor/foxess_modbus/wiki/Supported-Features).

Supported models:

- FoxESS H1 (including AC1, AIO-H1 and G2)
- FoxESS H3 (including AC3 and AOI-H3)
- FoxESS H3 PRO
- FoxESS P1
- FoxESS KH
- Kuara H3
- Sonnenkraft SK-HWR
- STAR
- Solavita SP
- a-TroniX AX
- Enpal
- 1KOMMA5°

You will need a direct connection to your inverter.
In most cases, this means buying a modbus to ethernet/USB adapter and wiring this to a port on your inverter.
See the documentation for details.

**[See the wiki](https://github.com/nathanmarlor/foxess_modbus/wiki) for how-to articles and FAQs.**

## Installation

[![Quick installation link](https://my.home-assistant.io/badges/hacs_repository.svg)][my-hacs]

Migrating from StealthChesnut's HA-FoxESS-Modbus? [Read this](https://github.com/nathanmarlor/foxess_modbus/wiki/Migrating-from-HA-FoxESS-Modbus).

This fork isn't in the HACS default list, so add it as a custom repository:

1. In HACS, open the three-dot menu and choose 'Custom repositories'
2. Add `https://github.com/MartB/foxess_modbus` with the category 'Integration'
3. Find 'FoxESS - Modbus (MartB fork)' in the list and download it
4. Restart Home Assistant
5. Go to Settings > Devices and Services > Add Integration
6. Search for and select 'FoxESS - Modbus' (If the integration is not found, empty your browser cache and reload the page)
7. Proceed with the configuration

## Usage

1. Navigate to Settings -> Devices & Services to find:

![Usage](images/usage.png)

2. Select '1 device' to find all Modbus readings:

![Example](images/example.png)

## Charge Periods

If your inverter supports setting charge periods, you can use install the [Charge Periods lovelace card](https://github.com/nathanmarlor/foxess_modbus_charge_period_card):

![Charge Periods](images/charge-periods.png)

## Services

### Write Service

A service to write any modbus address is available, similar to the native Home Assistant service. To use a service, navigate to Developer Tools -> Services and select it from the drop-down.

![Service](images/svc-write.png)

### Update Charge Periods

Updates one of the two charge periods (if supported by your inverter).

![Service](images/svc-charge-1.png)

### Update All Charge Periods

Sets all charge periods in one service call. The service "Update Charge Period" is easier for end-users to use.

![Service](images/svc-charge-2.png)

---

[buymecoffee]: https://www.buymeacoffee.com/nathanmarlor
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[hacs]: https://hacs.xyz
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=MartB&repository=foxess_modbus&category=integration
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[releases-shield]: https://img.shields.io/github/release/MartB/foxess_modbus.svg?style=for-the-badge
[releases]: https://github.com/MartB/foxess_modbus/releases
