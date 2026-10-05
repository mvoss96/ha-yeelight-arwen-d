# Yeelight Arwen for Home Assistant

Custom integration for the Yeelight Arwen ceiling light D600
(`yeelink.light.ceil43`), controlled entirely over the local network.

The official Xiaomi Home integration sends MIoT property writes, which carry no
fade time, and receives state changes through the Xiaomi cloud. The lamp does
not offer the Yeelight LAN protocol (TCP 55443). It does accept the Yeelight
command set over miIO (UDP 54321), including fade times and the effects of the
addressable main light. This integration uses those commands.

## Features

- **Main light**: on/off, brightness, color temperature (2700-6500 K), RGB,
  transitions.
- **Effects** on the main light: `Moonlight` (night light with its own
  brightness) and the 16 effects of the Mi Home app (Glittering, Pinball,
  Deep Sea, Rainbow, Green Shade, Ice Cream, Waxing Moon, Green Hills, Bonfire,
  Party, Garden, Winter, Heartbeat, Christmas, Sunset, Fantasy). The effect
  `off` returns to white light.
- **Ambient light**: on/off, brightness, color temperature, RGB, transitions.
- State is read locally every 3 s. The lamp sends no local push updates, so
  changes from the Mi Home app or the remote appear with up to 3 s delay.

Without a `transition` the lamp fades for 0.5 s, like the Mi Home app.
`transition: 0` switches instantly.

## Requirements

- Home Assistant 2025.8 or newer.
- The lamp's IP address (best made fixed in the router) and its 32-character
  miIO token, for example from
  [Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor).
  The token changes when the lamp is reset and paired again.

The lamp stays usable in the Mi Home app.

## Installation

Copy `custom_components/yeelight_arwen` into the `custom_components` folder of
the Home Assistant configuration, or add this repository to HACS as a custom
repository. Restart Home Assistant, add the integration **Yeelight Arwen** and
enter IP address and token.

## Protocol notes

Commands are sent without the `user.` prefix that the method names carry in the
firmware; prefixed calls are dropped silently.

| Function | Command |
|---|---|
| Power | `set_power ["on"/"off", "smooth", ms, mode]` with mode 1 = white, 2 = RGB, 5 = moonlight |
| Brightness / color temperature / color | `set_bright`, `set_ct_abx`, `set_rgb` with `"smooth", ms` |
| Moonlight | `set_scene ["nightlight", percent, "smooth", ms]` |
| Effect | `set_fx [1, index, "<preset>"]` |
| Ambient light | `bg_set_power`, `bg_set_bright`, `bg_set_ct_abx`, `bg_set_rgb` |
| State | `get_prop [...]` |

`color_mode` of the main light: 1 = RGB, 2 = white (moonlight when `nl_br` > 0),
14 = effect (`current_effect_index`). `bg_lmode` of the ambient light: 1 = RGB,
2 = white.

Debug logging of all sent commands:

```yaml
logger:
  logs:
    custom_components.yeelight_arwen: debug
```
