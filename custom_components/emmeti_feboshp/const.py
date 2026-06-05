"""Constants for Emmeti Febos HP.

https://github.com/teejay-87/ha-emmeti-feboshp
"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfFrequency, UnitOfPower, UnitOfTemperature

# Base component constants
NAME = "Emmeti Febos HP integration"
DOMAIN = "emmeti_feboshp"
VERSION = "1.3.2-beta.1"
ATTRIBUTION = "by @teejay-87, based on ha-4noks-elios4you by @alexdelprete"
ISSUE_URL = "https://github.com/teejay-87/ha-emmeti-feboshp/issues"

# Configuration and options
CONF_NAME = "name"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_NAME = "FebosHP"
DEFAULT_PORT = 5001
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 600
MIN_PORT = 1
MAX_PORT = 65535
CONN_TIMEOUT = 5
# Retry configuration for transient failures
COMMAND_RETRY_COUNT: int = 3  # Retry each command up to 3 times
COMMAND_RETRY_DELAY: float = 0.3  # 300ms delay between retries

# Repair notification options
CONF_ENABLE_REPAIR_NOTIFICATION = "enable_repair_notification"
CONF_FAILURES_THRESHOLD = "failures_threshold"
CONF_RECOVERY_SCRIPT = "recovery_script"
DEFAULT_ENABLE_REPAIR_NOTIFICATION = True
DEFAULT_FAILURES_THRESHOLD = 3
DEFAULT_RECOVERY_SCRIPT = ""
MIN_FAILURES_THRESHOLD = 1
MAX_FAILURES_THRESHOLD = 10

# Notification IDs
NOTIFICATION_RECOVERY = "recovery"
MANUFACTURER = "Emmeti"
MODEL = "FebosHP"
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME} - Version {VERSION}
{ATTRIBUTION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# Switch definitions

SWITCH_ENTITIES = [
    {
        "name": "Relay",
        "key": "relay_state",
        "icon": "mdi:toggle-switch-outline",
        "device_class": SwitchDeviceClass.SWITCH,
    },
]

# HP switch entities (controlled via @REG 1 <addr> <value> 1)
HP_SWITCH_ENTITIES = [
    {
        "name": "Heat Pump",
        "key": "hp_onoff",
        "icon": "mdi:heat-pump-outline",
        "device_class": SwitchDeviceClass.SWITCH,
        "register": 16384,
    },
    {
        "name": "Winter Mode",
        "key": "hp_winter_mode",
        "icon": "mdi:snowflake-thermometer",
        "device_class": SwitchDeviceClass.SWITCH,
        "register": 16385,
    },
    {
        "name": "Night Mode",
        "key": "hp_night_mode",
        "icon": "mdi:weather-night",
        "device_class": SwitchDeviceClass.SWITCH,
        "register": 16386,
    },
    {
        "name": "Turbo Mode",
        "key": "hp_turbo_mode",
        "icon": "mdi:rabbit",
        "device_class": SwitchDeviceClass.SWITCH,
        "register": 16387,
    },
]

# DAM 1 register map: (address, key, description, scale_divisor or None)
# scale_divisor: divide raw value by this to get the real value (10 = ÷10 for °C, 1000 = ÷1000 for kW)
DAM1_REGISTERS = [
    (8962, "hp_clock_year", None),
    (8963, "hp_clock_month", None),
    (8964, "hp_clock_day", None),
    (8965, "hp_clock_hour", None),
    (8966, "hp_clock_minute", None),
    (8986, "hp_external_temp", 10),
    (8987, "hp_water_outlet_temp", 10),
    (8988, "hp_water_inlet_temp", 10),
    (8989, "hp_dhw_setpoint", 10),
    (8993, "hp_ambient_temp", 10),
    (8995, "hp_dew_point_temp", 10),
    (8999, "hp_valve_0", None),
    (9000, "hp_valve_1", None),
    (9001, "hp_valve_2", None),
    (9002, "hp_valve_3", None),
    (9003, "hp_valve_4", None),
    (9004, "hp_valve_5", None),
    (9005, "hp_valve_6", None),
    (9007, "hp_circulation_pump", None),
    (9018, "hp_consumed_power", 1000),
    (9020, "hp_heating_power", 1000),
    (9022, "hp_cooling_power", 1000),
    (9036, "hp_dhw_power", 1000),
    (9064, "hp_dam_9064", None),
    (9076, "hp_target_reached", None),
    (9080, "hp_active_profile", None),
    (9085, "hp_ambient_setpoint", 10),
    (9087, "hp_water_target_temp", 10),
    (9088, "hp_water_actual_temp", 10),
    (9091, "hp_compressor_freq", None),
    (16384, "hp_onoff", None),
    (16385, "hp_winter_mode", None),
    (16386, "hp_night_mode", None),
    (16387, "hp_turbo_mode", None),
]

# HP sensor entity definitions (from DAM 1)
HP_SENSOR_ENTITIES = [
    {
        "name": "HP External Temperature",
        "key": "hp_external_temp",
        "icon": "mdi:thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "enabled_default": True,
    },
    {
        "name": "HP Water Outlet Temperature",
        "key": "hp_water_outlet_temp",
        "icon": "mdi:thermometer-water",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "enabled_default": True,
    },
    {
        "name": "HP Water Inlet Temperature",
        "key": "hp_water_inlet_temp",
        "icon": "mdi:thermometer-water",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "enabled_default": True,
    },
    {
        "name": "HP DHW Setpoint",
        "key": "hp_dhw_setpoint",
        "icon": "mdi:water-thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "enabled_default": True,
    },
    {
        "name": "HP Ambient Temperature",
        "key": "hp_ambient_temp",
        "icon": "mdi:home-thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "enabled_default": True,
    },
    {
        "name": "HP Dew Point Temperature",
        "key": "hp_dew_point_temp",
        "icon": "mdi:water-thermometer-outline",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "enabled_default": False,
    },
    {
        "name": "HP Ambient Setpoint",
        "key": "hp_ambient_setpoint",
        "icon": "mdi:thermostat",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "enabled_default": True,
    },
    {
        "name": "HP Water Target Temperature",
        "key": "hp_water_target_temp",
        "icon": "mdi:thermometer-chevron-up",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "enabled_default": True,
    },
    {
        "name": "HP Water Actual Temperature",
        "key": "hp_water_actual_temp",
        "icon": "mdi:thermometer-check",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "enabled_default": True,
    },
    {
        "name": "HP Consumed Power",
        "key": "hp_consumed_power",
        "icon": "mdi:flash",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "HP Heating Power",
        "key": "hp_heating_power",
        "icon": "mdi:fire",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "HP Cooling Power",
        "key": "hp_cooling_power",
        "icon": "mdi:snowflake",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "HP DHW Power",
        "key": "hp_dhw_power",
        "icon": "mdi:water-boiler",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "HP Compressor Frequency",
        "key": "hp_compressor_freq",
        "icon": "mdi:sine-wave",
        "device_class": SensorDeviceClass.FREQUENCY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfFrequency.HERTZ,
        "enabled_default": True,
    },
    {
        "name": "HP Active Profile",
        "key": "hp_active_profile",
        "icon": "mdi:calendar-clock",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": True,
    },
    {
        "name": "HP Target Reached",
        "key": "hp_target_reached",
        "icon": "mdi:check-circle-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": True,
    },
    {
        "name": "HP Circulation Pump",
        "key": "hp_circulation_pump",
        "icon": "mdi:pump",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "HP Valve 0",
        "key": "hp_valve_0",
        "icon": "mdi:valve",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "HP Valve 1",
        "key": "hp_valve_1",
        "icon": "mdi:valve",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "HP Valve 2",
        "key": "hp_valve_2",
        "icon": "mdi:valve",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "HP Valve 3",
        "key": "hp_valve_3",
        "icon": "mdi:valve",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "HP Valve 4",
        "key": "hp_valve_4",
        "icon": "mdi:valve",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "HP Valve 5",
        "key": "hp_valve_5",
        "icon": "mdi:valve",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "HP Valve 6",
        "key": "hp_valve_6",
        "icon": "mdi:valve",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
]

# Sensor definitions
# enabled_default: True = enabled by default, False = disabled by default (user can enable manually)
# F1/F2/F3 time-of-use variants and diagnostic sensors are disabled by default to reduce clutter
SENSOR_ENTITIES = [
    {
        "name": "Produced Power",
        "key": "produced_power",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Consumed Power",
        "key": "consumed_power",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Self Consumed Power",
        "key": "self_consumed_power",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Bought Power",
        "key": "bought_power",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Sold Power",
        "key": "sold_power",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Daily Peak",
        "key": "daily_peak",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Monthly Peak",
        "key": "monthly_peak",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Produced Energy",
        "key": "produced_energy",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Produced Energy F1",
        "key": "produced_energy_f1",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Produced Energy F2",
        "key": "produced_energy_f2",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Produced Energy F3",
        "key": "produced_energy_f3",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Consumed Energy",
        "key": "consumed_energy",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Consumed Energy F1",
        "key": "consumed_energy_f1",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Consumed Energy F2",
        "key": "consumed_energy_f2",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Consumed Energy F3",
        "key": "consumed_energy_f3",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Self Consumed Energy",
        "key": "self_consumed_energy",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Self Consumed Energy F1",
        "key": "self_consumed_energy_f1",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Self Consumed Energy F2",
        "key": "self_consumed_energy_f2",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Self Consumed Energy F3",
        "key": "self_consumed_energy_f3",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Bought Energy",
        "key": "bought_energy",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Bought Energy F1",
        "key": "bought_energy_f1",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Bought Energy F2",
        "key": "bought_energy_f2",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Bought Energy F3",
        "key": "bought_energy_f3",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Sold Energy",
        "key": "sold_energy",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Sold Energy F1",
        "key": "sold_energy_f1",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Sold Energy F2",
        "key": "sold_energy_f2",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Sold Energy F3",
        "key": "sold_energy_f3",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Alarm 1",
        "key": "alarm_1",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Alarm 2",
        "key": "alarm_2",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Power Alarm",
        "key": "power_alarm",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "PWM Mode",
        "key": "pwm_mode",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Power Reducer Ssv",
        "key": "pr_ssv",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Relay Ssv",
        "key": "rel_ssv",
        "icon": "mdi:toggle-switch-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Relay Mode",
        "key": "rel_mode",
        "icon": "mdi:toggle-switch-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Relay Warning",
        "key": "rel_warning",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "RedCap",
        "key": "rcap",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Firmware TOP Version",
        "key": "fwtop",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Firmware BOTTOM Version",
        "key": "fwbtm",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Serial Number",
        "key": "sn",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Hardware Version",
        "key": "hwver",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "BT Version",
        "key": "btver",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Wifi HW Version",
        "key": "hw_wifi",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Wifi App Version",
        "key": "s2w_app_version",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Wifi Geps Version",
        "key": "s2w_geps_version",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Wifi Wlan Version",
        "key": "s2w_wlan_version",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    # ---- ConnectionManager diagnostic sensors ----
    # All routed to DIAGNOSTIC entity category (state_class=None triggers that
    # in sensor.py). Four are enabled by default so users see connection health
    # without enabling anything: cm_state + cm_consecutive_failures (link
    # status), cm_silent_timeouts (the only signal for auto-recovered "deaf
    # device" events), and cm_last_error (diagnosis). The rest are opt-in.
    {
        "name": "Connection State",
        "key": "cm_state",
        "icon": "mdi:lan-connect",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": True,
    },
    {
        "name": "Connection Consecutive Failures",
        "key": "cm_consecutive_failures",
        "icon": "mdi:alert-circle-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": True,
    },
    {
        "name": "Connection Backoff Remaining",
        "key": "cm_backoff_seconds_remaining",
        "icon": "mdi:timer-sand",
        "device_class": None,
        "state_class": None,
        "unit": "s",
        "enabled_default": False,
    },
    {
        "name": "Connection Connects Succeeded",
        "key": "cm_connects_succeeded",
        "icon": "mdi:lan-pending",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Connection Connect Failures",
        "key": "cm_connect_failures",
        "icon": "mdi:lan-disconnect",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Connection Reuse Hits",
        "key": "cm_reuse_hits",
        "icon": "mdi:reload",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Connection Commands Sent",
        "key": "cm_commands_sent",
        "icon": "mdi:send",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Connection Commands Failed",
        "key": "cm_commands_failed",
        "icon": "mdi:send-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Connection Commands Retried",
        "key": "cm_commands_retried",
        "icon": "mdi:restart",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Connection Silent Timeouts",
        "key": "cm_silent_timeouts",
        "icon": "mdi:volume-off",
        "device_class": None,
        "state_class": None,
        "unit": None,
        # Enabled by default: this is the ONLY signal that surfaces a
        # "device went deaf" event. Auto-recovery resets consecutive_failures
        # and keeps cm_state=ready, so the other defaults never reveal it.
        "enabled_default": True,
    },
    {
        "name": "Connection Forced Aborts",
        "key": "cm_forced_aborts",
        "icon": "mdi:close-octagon-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Connection Last Error",
        "key": "cm_last_error",
        "icon": "mdi:message-alert-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        # Enabled by default: empty when healthy, but the most useful field for
        # diagnosing a problem / filing a bug report.
        "enabled_default": True,
    },
]
