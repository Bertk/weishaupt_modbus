"""Constants."""

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)

CONF_DEVICE_POSTFIX = "Device-Postfix"
CONF_KENNFELD_FILE = "Kennfeld-File"
CONF_HK2 = "Heizkreis 2"
CONF_HK3 = "Heizkreis 3"
CONF_HK4 = "Heizkreis 4"
CONF_HK5 = "Heizkreis 5"
CONF_NAME_DEVICE_PREFIX = "Name-Device-Prefix"
CONF_NAME_TOPIC_PREFIX = "Name-Topic-Prefix"

name_list = []


@dataclass(frozen=True)
class MainConstants:
    """Main constants."""

    DOMAIN = "weishaupt_modbus"
    SCAN_INTERVAL = timedelta(seconds=30)
    UNIQUE_ID = "unique_id"
    APPID = 100
    DEF_KENNFELDFILE = "weishaupt_wbb_kennfeld.json"
    DEF_PREFIX = "weishaupt_wbb"


CONST = MainConstants()


@dataclass(frozen=True)
class FormatConstants:
    """Format constants."""

    TEMPERATUR = UnitOfTemperature.CELSIUS
    ENERGY = UnitOfEnergy.KILO_WATT_HOUR
    POWER = UnitOfPower.WATT
    PERCENTAGE = PERCENTAGE
    NUMBER = ""
    STATUS = "Status"
    VOLUMENSTROM = UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
    KENNLINIE = " "  # has to be different from NUMBER we'd have to separate unit strings and format...
    TIME_MIN = UnitOfTime.MINUTES
    TIME_H = UnitOfTime.HOURS
    UNKNOWN = "?"


FORMATS = FormatConstants()


@dataclass(frozen=True)
class TypeConstants:
    """Type constants."""

    SENSOR = "Sensor"
    SENSOR_CALC = "Sensor_Calc"
    SELECT = "Select"
    NUMBER = "Number"
    NUMBER_RO = "Number_RO"


TYPES = TypeConstants()


@dataclass(frozen=True)
class DeviceConstants:
    """Device constants."""

    SYS = "dev_system"
    WP = "dev_waermepumpe"
    WW = "dev_warmwasser"
    HZ = "dev_heizkreis"
    HZ2 = "dev_heizkreis2"
    HZ3 = "dev_heizkreis3"
    HZ4 = "dev_heizkreis4"
    HZ5 = "dev_heizkreis5"
    W2 = "dev_waermeerzeuger2"
    ST = "dev_statistik"
    UK = "dev_unknown"
    IO = "dev_ein_aus"
    # SYS = "System"
    # WP = "Wärmepumpe"
    # WW = "Warmwasser"
    # HZ = "Heizkreis"
    # HZ2 = "Heizkreis2"
    # HZ3 = "Heizkreis3"
    # HZ4 = "Heizkreis4"
    # HZ5 = "Heizkreis5"
    # W2 = "2. Wärmeerzeuger"
    # ST = "Statistik"
    # UK = "Unknown"
    # IO = "Eingänge/Ausgänge"


DEVICES = DeviceConstants()
