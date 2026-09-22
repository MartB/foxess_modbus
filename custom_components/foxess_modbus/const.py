"""Constants for foxess_modbus."""

from typing import Any

# Base component constants
NAME = "foxess_modbus"
DOMAIN = "foxess_modbus"
DOMAIN_DATA = f"{DOMAIN}_data"

ISSUE_URL = "https://github.com/nathanmarlor/foxess_modbus/issues"

# Icons
ICON = "mdi:format-quote-close"

# Platforms
SENSOR = "sensor"
BINARY_SENSOR = "binary_sensor"
SELECT = "select"
NUMBER = "number"
PLATFORMS = [SENSOR, BINARY_SENSOR, SELECT, NUMBER]
ATTR_ENTRY_TYPE = "entry_type"

# Modbus Options
# Once upon a time, we just had the friendly name, and we allowed any string. We added this to the start of all entity
# IDs and unique IDs. HA converted the resulting entity IDs to be valid (replacing spaces with _, etc), but this caused
# problems with e.g. the energy dashboard.
# Then we moved to a separate friendly name (shown in the entity name) and entity ID prefix (added to the start of
# entity and unique IDs). This was always a valid entity ID for new configs, but could still be invalid for old migrated
# configs. This fixed the problem with the energy dashboard. However, the charge period card still got tripped up by
# entity ID prefixes which were invalid entity IDs.
# We then migrated all entity ID prefix to be valid entity IDs. However, this broke the fact that we were also using the
# entity ID prefix as the unique ID prefix. Therefore we added the UNIQUE_ID_PREFIX. For old configs with an old invalid
# entity ID prefix, the unique ID prefix retains the old invalid value while the entity ID prefix is fixed. For new
# configs, it should be the same as the entity ID prefix.
ENTITY_ID_PREFIX = "entity_id_prefix"
# Set at runtime, once the inverter's device registry entry exists, so that the devices underneath it
# can say which device they hang off. Home Assistant wants that as a registry id, not an identifier
INVERTER_DEVICE_ID = "inverter_device_id"
UNIQUE_ID_PREFIX = "unique_id_prefix"
FRIENDLY_NAME = "friendly_name"
MODBUS_SLAVE = "modbus_slave"
MODBUS_DEVICE = "modbus_device"
MODBUS_TYPE = "modbus_type"  # TCP, UDP, SERIAL, RTU_OVER_TCP
MODBUS_SERIAL_BAUD = "modbus_serial_baud"
POLL_RATE = "poll_rate"
MAX_READ = "max_read"
ADAPTER_ID = "adapter_id"
ROUND_SENSOR_VALUES = "round_sensor_values"
# Used as a key in the inverter config to indicate that the adapter was migrated from config version 1
ADAPTER_WAS_MIGRATED = "adapter_was_migrated"

# In a parallel installation only the master drives remote control, sizing its single command from the
# combined battery limits of the whole cluster
REMOTE_CONTROL_ROLE = "remote_control_role"
REMOTE_CONTROL_ROLE_STANDALONE = "standalone"  # default: independent, unchanged behaviour
REMOTE_CONTROL_ROLE_MASTER = "master"
REMOTE_CONTROL_ROLE_SLAVE = "slave"

# A master links only with slaves sharing this id, so several clusters can coexist in one config entry
REMOTE_CONTROL_CLUSTER = "remote_control_cluster"
REMOTE_CONTROL_CLUSTER_DEFAULT = "1"

# Work mode the inverter returns to when a force charge/discharge ends, e.g. at max SoC
REMOTE_CONTROL_FALLBACK_WORK_MODE = "remote_control_fallback_work_mode"
REMOTE_CONTROL_FALLBACK_SELF_USE = "self_use"
REMOTE_CONTROL_FALLBACK_FEED_IN_FIRST = "feed_in_first"
REMOTE_CONTROL_FALLBACK_BACK_UP = "back_up"
REMOTE_CONTROL_FALLBACK_DEFAULT = REMOTE_CONTROL_FALLBACK_BACK_UP


def is_remote_control_slave(inverter_details: dict[str, Any]) -> bool:
    """A slave has no remote control of its own, so mustn't expose force charge/discharge controls"""
    return inverter_details.get(REMOTE_CONTROL_ROLE) == REMOTE_CONTROL_ROLE_SLAVE


INVERTER_MODEL = "inverter_model"
INVERTER_BASE = "inverter_base"
INVERTER_CONN = "inverter_conn"
# The inverter manager version to use. This is the version corresponding to InverterModelConnectionTypeProfile.versions,
# i.e. the upper bound of a range of versions we support. None means use the latest.
INVERTER_VERSION = "inverter_version"
INVERTERS = "inverters"

CONFIG_SAVE_TIME = "save_time"

HOST = "host"
TCP = "tcp"
UDP = "udp"
SERIAL = "serial"
RTU_OVER_TCP = "rtu_over_tcp"

CONTROLLER = "controllers"
CONFIG = "config"
INVERTER = "inverter"
CONNECTION = "connection"
MODBUS = "modbus"

CONFIG_ENTRY_TITLE = "FoxESS - Modbus"

# Defaults
DEFAULT_NAME = DOMAIN

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
