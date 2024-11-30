"""Build entitiy List and Update Coordinator."""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import CONF_PORT, CONF_PREFIX
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_POSTFIX,
    CONF_HK2,
    CONF_HK3,
    CONF_HK4,
    CONF_HK5,
    CONF_NAME_DEVICE_PREFIX,
    CONF_NAME_TOPIC_PREFIX,
    CONST,
    DEVICES,
    FORMATS,
    TYPES,
)

from .coordinator import MyCoordinator
from .hpconst import reverse_device_list
from .items import ModbusItem
from .kennfeld import PowerMap
from .modbusobject import ModbusAPI, ModbusObject
from .configentry import MyConfigEntry
from .migrate_helpers import create_unique_id

logging.basicConfig()
log = logging.getLogger(__name__)


async def check_available(modbus_item: ModbusItem, config_entry: MyConfigEntry) -> bool:
    """function checks if item is valid and available

    :param config_entry: HASS config entry
    :type config_entry: MyConfigEntry
    :param modbus_item: definition of modbus item
    :type modbus_item: ModbusItem
    """
    log.debug("Check if item %s is available ..", modbus_item.name)
    if config_entry.data[CONF_HK2] is False:
        if modbus_item.device is DEVICES.HZ2:
            return False

    if config_entry.data[CONF_HK3] is False:
        if modbus_item.device is DEVICES.HZ3:
            return False

    if config_entry.data[CONF_HK4] is False:
        if modbus_item.device is DEVICES.HZ4:
            return False

    if config_entry.data[CONF_HK5] is False:
        if modbus_item.device is DEVICES.HZ5:
            return False

    _modbus_api = config_entry.runtime_data.modbus_api
    mbo = ModbusObject(_modbus_api, modbus_item)
    _useless = await mbo.value
    if modbus_item.is_invalid is False:
        log.debug("Check availability item %s successful ..", modbus_item.name)
        return True
    return False


async def build_entity_list(
    entries,
    config_entry: MyConfigEntry,
    modbusitems: ModbusItem,
    item_type,
    coordinator: MyCoordinator,
):
    """Build entity list.

    function builds a list of entities that can be used as parameter by async_setup_entry()
    type of list is defined by the ModbusItem's type flag
    so the app only holds one list of entities that is build from a list of ModbusItem
    stored in hpconst.py so far, will be provided by an external file in future

    :param config_entry: HASS config entry
    :type config_entry: MyConfigEntry
    :param modbus_item: definition of modbus item
    :type modbus_item: ModbusItem
    :param item_type: type of modbus item
    :type item_type: TYPES
    :param coordinator: the update coordinator
    :type coordinator: MyCoordinator
    """
    for index, item in enumerate(modbusitems):
        if item.type == item_type:
            if await check_available(item, config_entry=config_entry) is True:
                log.debug("Add item %s to entity list ..", item.name)
                match item_type:
                    # here the entities are created with the parameters provided
                    # by the ModbusItem object
                    case TYPES.SENSOR | TYPES.NUMBER_RO:
                        entries.append(
                            MySensorEntity(config_entry, item, coordinator, index)
                        )
                    case TYPES.SENSOR_CALC:
                        pwrmap = PowerMap(config_entry)
                        await pwrmap.initialize()
                        entries.append(
                            MyCalcSensorEntity(
                                config_entry,
                                item,
                                coordinator,
                                index,
                                pwrmap,
                            )
                        )
                    case TYPES.SELECT:
                        entries.append(
                            MySelectEntity(config_entry, item, coordinator, index)
                        )
                    case TYPES.NUMBER:
                        entries.append(
                            MyNumberEntity(config_entry, item, coordinator, index)
                        )

    return entries


class MyEntity(Entity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
    should_poll
    async_update
    async_added_to_hass
    available

    The base class for entities that hold general parameters
    """

    _config_entry = None
    _modbus_item = None
    _divider = 1
    _attr_unique_id = ""
    _attr_should_poll = True
    _attr_translation_key = ""
    _attr_has_entity_name = True
    _dev_device = ""
    _modbus_api = None

    def __init__(
        self,
        config_entry: MyConfigEntry,
        modbus_item: ModbusItem,
        modbus_api: ModbusAPI,
    ) -> None:
        """Initialize the entity."""
        self._config_entry = config_entry
        self._modbus_item = modbus_item

        dev_postfix = "_" + self._config_entry.data[CONF_DEVICE_POSTFIX]

        if dev_postfix == "_":
            dev_postfix = ""

        dev_prefix = self._config_entry.data[CONF_PREFIX]

        if self._config_entry.data[CONF_NAME_DEVICE_PREFIX]:
            name_device_prefix = dev_prefix + "_"
        else:
            name_device_prefix = ""

        if self._config_entry.data[CONF_NAME_TOPIC_PREFIX]:
            name_topic_prefix = reverse_device_list[self._modbus_item.device] + "_"
        else:
            name_topic_prefix = ""

        name_prefix = name_topic_prefix + name_device_prefix

        self._attr_translation_key = self._modbus_item.translation_key
        self._attr_translation_placeholders = {"prefix": name_prefix}
        self._dev_translation_placeholders = {"postfix": dev_postfix}

        self._attr_unique_id = create_unique_id(self._config_entry, self._modbus_item)
        self._dev_device = self._modbus_item.device

        self._modbus_api = modbus_api

        if self._modbus_item._format != FORMATS.STATUS:
            self._attr_native_unit_of_measurement = self._modbus_item._format

            match self._modbus_item._format:
                case FORMATS.ENERGY:
                    self._attr_state_class = SensorStateClass.TOTAL_INCREASING
                case (
                    FORMATS.TEMPERATUR
                    | FORMATS.POWER
                    | FORMATS.PERCENTAGE
                    | FORMATS.TIME_H
                    | FORMATS.TIME_MIN
                    | FORMATS.UNKNOWN
                ):
                    self._attr_state_class = SensorStateClass.MEASUREMENT

            if self._modbus_item.params is not None:
                self._attr_native_min_value = self._modbus_item.params["min"]
                self._attr_native_max_value = self._modbus_item.params["max"]
                self._attr_native_step = self._modbus_item.params["step"]
                self._divider = self._modbus_item.params["divider"]
                self._attr_device_class = self._modbus_item.params["deviceclass"]

    def translate_val(self, val) -> float:
        """Translate modbus value into sensful format."""
        if self._modbus_item.format == FORMATS.STATUS:
            return self._modbus_item.get_translation_key_from_number(val)
        else:
            if val is None:
                return None
            return val / self._divider

    def retranslate_val(self, value) -> int:
        """Re-translate modbus value into sensful format."""
        if self._modbus_item.format == FORMATS.STATUS:
            return self._modbus_item.get_number_from_translation_key(value)
        else:
            return int(value * self._divider)

    async def set_translate_val(self, value) -> None:
        """Translate and writes a value to the modbus."""
        val = self.retranslate_val(value)

        await self._modbus_api.connect()
        mbo = ModbusObject(self._modbus_api, self._modbus_item)
        await mbo.setvalue(val)

    def my_device_info(self) -> DeviceInfo:
        """Build the device info."""
        return {
            "identifiers": {(CONST.DOMAIN, self._dev_device)},
            "translation_key": self._dev_device,
            "translation_placeholders": self._dev_translation_placeholders,
            "sw_version": "Device_SW_Version",
            "model": "Device_model",
            "manufacturer": "Weishaupt",
        }


class MySensorEntity(CoordinatorEntity, SensorEntity, MyEntity):
    """Class that represents a sensor entity.

    Derived from Sensorentity
    and decorated with general parameters from MyEntity
    """

    _attr_native_unit_of_measurement = None
    _attr_device_class = None
    _attr_state_class = None
    _renamed = False

    def __init__(
        self,
        config_entry: MyConfigEntry,
        modbus_item: ModbusItem,
        coordinator: MyCoordinator,
        idx,
    ) -> None:
        super().__init__(coordinator, context=idx)
        self.idx = idx
        MyEntity.__init__(self, config_entry, modbus_item, coordinator._modbus_api)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.translate_val(self._modbus_item.state)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return MyEntity.my_device_info(self)


class MyCalcSensorEntity(MySensorEntity):
    """class that represents a sensor entity.

    Derived from Sensorentity
    and decorated with general parameters from MyEntity
    """

    # calculates output from map
    my_map = None

    def __init__(
        self,
        config_entry: MyConfigEntry,
        modbus_item: ModbusItem,
        coordinator: MyCoordinator,
        idx,
        pwrmap: PowerMap,
    ) -> None:
        MySensorEntity.__init__(self, config_entry, modbus_item, coordinator, idx)
        self.my_map = pwrmap

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.translate_val(self._modbus_item.state)
        self.async_write_ha_state()

    def calc_power(self, val, x, y):
        """Calculate heating power from power map."""
        if val is None:
            return val
        return (val / 100) * self.my_map.map(x, y)

    def translate_val(self, val):
        """Translate a value from the modbus."""
        # this is necessary to avoid errors when re-connection heatpump
        if val is None:
            return None
        if len(val) < 3:
            return None
        if val[0] is None:
            return None
        if val[1] is None:
            return None
        if val[2] is None:
            return None

        val_0 = val[0] / self._divider
        val_x = val[1] / 10
        val_y = val[2] / 10

        match self._modbus_item.format:
            case FORMATS.POWER:
                return round(self.calc_power(val_0, val_x, val_y))
            case _:
                if val_0 is None:
                    return None
                return val_0


class MyNumberEntity(CoordinatorEntity, NumberEntity, MyEntity):
    """class that represents a sensor entity derived from Sensorentity
    and decorated with general parameters from MyEntity
    """

    _attr_native_unit_of_measurement = None
    _attr_device_class = None
    _attr_state_class = None
    _attr_native_min_value = 10
    _attr_native_max_value = 60

    def __init__(
        self,
        config_entry: MyConfigEntry,
        modbus_item: ModbusItem,
        coordinator: MyCoordinator,
        idx,
    ) -> None:
        """Initialize NyNumberEntity."""
        super().__init__(coordinator, context=idx)
        self._idx = idx
        MyEntity.__init__(self, config_entry, modbus_item, coordinator._modbus_api)

        # if self._modbus_item.resultlist is not None:
        #    self._attr_native_min_value = self._modbus_item.get_number_from_text("min")
        #    self._attr_native_max_value = self._modbus_item.get_number_from_text("max")
        #    self._attr_native_step = self._modbus_item.get_number_from_text("step")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.translate_val(self._modbus_item.state)
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        await self.set_translate_val(value)
        self._modbus_item.state = int(self.retranslate_val(value))
        self._attr_native_value = self.translate_val(self._modbus_item.state)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return MyEntity.my_device_info(self)


class MySelectEntity(CoordinatorEntity, SelectEntity, MyEntity):
    """class that represents a sensor entity derived from Sensorentity
    and decorated with general parameters from MyEntity
    """

    options = []
    _attr_current_option = "FEHLER"

    def __init__(
        self,
        config_entry: MyConfigEntry,
        modbus_item: ModbusItem,
        coordinator: MyCoordinator,
        idx,
    ) -> None:
        """Initialze MySelectEntity."""
        super().__init__(coordinator, context=idx)
        self._idx = idx
        MyEntity.__init__(self, config_entry, modbus_item, coordinator._modbus_api)

        self.async_internal_will_remove_from_hass_port = self._config_entry.data[
            CONF_PORT
        ]
        # option list build from the status list of the ModbusItem
        self.options = []
        for _useless, item in enumerate(self._modbus_item._resultlist):
            self.options.append(item.translation_key)

    async def async_select_option(self, option: str) -> None:
        # the synching is done by the ModbusObject of the entity
        await self.set_translate_val(option)
        self._modbus_item.state = int(self.retranslate_val(option))
        self._attr_current_option = self.translate_val(self._modbus_item.state)
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_current_option = self.translate_val(self._modbus_item.state)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return MyEntity.my_device_info(self)
