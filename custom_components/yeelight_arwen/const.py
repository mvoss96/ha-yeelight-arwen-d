"""Constants for the Yeelight Arwen integration."""

from datetime import timedelta

DOMAIN = "yeelight_arwen"
SUPPORTED_MODELS = ("yeelink.light.ceil43",)
SCAN_INTERVAL = timedelta(seconds=3)
# Minimum seconds between two broadcast searches for a lamp that stopped answering.
REDISCOVERY_INTERVAL = 60

CONF_DID = "did"

# Properties read with get_prop; the same list the Mi Home plugin uses, minus unused ones.
PROPS = (
    "main_power", "bright", "ct", "rgb", "color_mode", "nl_br", "current_effect_index",
    "bg_power", "bg_bright", "bg_ct", "bg_rgb", "bg_lmode",
)

# color_mode values of the main light.
COLOR_MODE_RGB = 1
COLOR_MODE_CT = 2
COLOR_MODE_FLOW = 14

# Last parameter of set_power / bg_set_power: the mode the light switches into.
POWER_MODE_CT = 1
POWER_MODE_RGB = 2
POWER_MODE_MOONLIGHT = 5

MIN_KELVIN = 2700
MAX_KELVIN = 6500

EFFECT_MOONLIGHT = "Moonlight"

# Effects of the addressable main light: name -> set_fx parameters (from Mi Home plugin v13).
EFFECTS = {
    "Glittering": [1, 1, "4,192,128,100,255,1,255"],
    "Pinball": [1, 2, "5,192,128,100,255,1,255"],
    "Deep Sea": [1, 3, "9,192,128,100,255,1,255"],
    "Rainbow": [1, 4, "17,192,128,100,255,1,255"],
    "Green Shade": [1, 5, "20,192,200,100,255,1,255"],
    "Ice Cream": [1, 11, "26,192,200,100,255,1,255"],
    "Waxing Moon": [1, 9, "24,192,200,100,255,1,255"],
    "Green Hills": [1, 14, "29,192,200,100,255,1,255"],
    "Bonfire": [1, 15, "30,192,200,100,255,1,255"],
    "Party": [1, 6, "21,192,200,100,255,1,255"],
    "Garden": [1, 8, "23,192,200,100,255,1,255"],
    "Winter": [1, 12, "27,192,200,100,255,1,255"],
    "Heartbeat": [1, 13, "28,192,200,100,255,1,255"],
    "Christmas": [1, 10, "25,192,200,100,255,1,255"],
    "Sunset": [1, 7, "22,192,200,100,255,1,255"],
    "Fantasy": [1, 16, "31,192,200,100,255,1,255"],
}
EFFECT_BY_INDEX = {params[1]: name for name, params in EFFECTS.items()}
