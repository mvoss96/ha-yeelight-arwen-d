"""Constants for the Yeelight Arwen D integration."""

from datetime import timedelta

DOMAIN = "yeelight_arwen_d"
MODEL_ARWEN_D = "yeelink.light.ceil43"
MODEL_CEILING3 = "yeelink.light.ceiling3"
SUPPORTED_MODELS = (MODEL_ARWEN_D, MODEL_CEILING3)
# Device name per model.
MODEL_NAMES = {MODEL_ARWEN_D: "Yeelight Arwen D", MODEL_CEILING3: "Yeelight Ceiling3"}
SCAN_INTERVAL = timedelta(seconds=3)
# Poll interval while the lamp pushes its state changes over the Yeelight LAN protocol.
PUSH_SCAN_INTERVAL = timedelta(seconds=60)
# Yeelight LAN protocol port; only the ceiling3 offers it.
LAN_PORT = 55443
# Minimum seconds between two broadcast searches for a lamp that stopped answering.
REDISCOVERY_INTERVAL = 60
# Minimum seconds between two reads of miIO.info (Wi-Fi signal, uptime).
INFO_INTERVAL = 60

CONF_DID = "did"

# Properties read with get_prop; the same list the Mi Home plugin uses, minus unused ones.
PROPS = (
    "main_power", "bright", "ct", "rgb", "color_mode", "nl_br", "current_effect_index",
    "bg_power", "bg_bright", "bg_ct", "bg_rgb", "bg_lmode",
    "trans_interval_dflt", "power_on_effect", "bg_proact", "save_state", "smart_switch",
)
# Properties of the ceiling3: white light and night light only. active_mode is 1 in night light.
PROPS_CEILING3 = ("power", "bright", "ct", "nl_br", "active_mode", "trans_interval_dflt")

# On/off settings of the Mi Home app: key -> (property read with get_prop, name written with set_ps, entity name).
SWITCH_SETTINGS = {
    "ambient_follows": ("bg_proact", "cfg_bg_proact", "Ambient follows primary light"),
    "remember_state": ("save_state", "cfg_save_state", "Remember last state"),
    "wall_switch": ("smart_switch", "cfg_smart_switch", "Wall switch mode"),
}

# color_mode values of the main light.
COLOR_MODE_RGB = 1
COLOR_MODE_CT = 2
COLOR_MODE_FLOW = 14

# Last parameter of set_power / bg_set_power: the mode the light switches into.
POWER_MODE_CT = 1
POWER_MODE_RGB = 2
POWER_MODE_NIGHT_LIGHT = 5

MIN_KELVIN = 2700
MAX_KELVIN = 6500

EFFECT_NIGHT_LIGHT = "Night light"

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
