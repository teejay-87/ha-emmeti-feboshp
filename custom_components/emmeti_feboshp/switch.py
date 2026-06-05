"""Switch Platform Device for Emmeti Febos HP.

https://github.com/teejay-87/ha-emmeti-feboshp
"""

import asyncio
import logging
from typing import Any, cast

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FebosHPConfigEntry
from .const import DEFAULT_PAUSE_DURATION, DOMAIN, HP_SWITCH_ENTITIES, SWITCH_ENTITIES
from .coordinator import FebosHPCoordinator
from .helpers import log_debug

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: FebosHPConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Switch Platform setup."""

    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator = config_entry.runtime_data.coordinator

    # Add defined switches using list comprehension. SWITCH_ENTITIES is a list
    # of heterogeneous dicts (str names/keys/icons + SwitchDeviceClass), so we
    # cast each entry to ``dict[str, Any]`` to bypass per-value type narrowing
    # — matches the pattern used in sensor.py.
    switches = [
        FebosHPSwitch(
            coordinator,
            switch_def["name"],
            switch_def["key"],
            switch_def["icon"],
            switch_def["device_class"],
        )
        for switch in SWITCH_ENTITIES
        for switch_def in (cast(dict[str, Any], switch),)
        if coordinator.api.data[switch_def["key"]] is not None
    ]

    # Add HP register-based switches
    for switch in HP_SWITCH_ENTITIES:
        switch_def = cast(dict[str, Any], switch)
        if coordinator.api.data.get(switch_def["key"]) is not None:
            switches.append(
                FebosHPRegisterSwitch(
                    coordinator,
                    switch_def["name"],
                    switch_def["key"],
                    switch_def["icon"],
                    switch_def["device_class"],
                    switch_def["register"],
                )
            )

    # Add Pause Polling switch
    switches.append(FebosHPPauseSwitch(coordinator))

    async_add_entities(switches)

    return True


class FebosHPSwitch(CoordinatorEntity[FebosHPCoordinator], SwitchEntity):
    """Switch to set the status of the Wiser Operation Mode (Away/Normal)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FebosHPCoordinator,
        name: str,
        key: str,
        icon: str,
        device_class: SwitchDeviceClass,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._key = key
        self._icon = icon
        self._device_class = device_class
        self._is_on = self._coordinator.api.data["relay_state"]
        self._device_name: str = str(self._coordinator.api.name)
        self._device_host = self._coordinator.api.host
        self._device_model: str = str(self._coordinator.api.data["model"])
        self._device_manufact: str = str(self._coordinator.api.data["manufact"])
        self._device_sn: str = str(self._coordinator.api.data["sn"])
        self._device_swver: str = str(self._coordinator.api.data["swver"])
        self._device_hwver: str = str(self._coordinator.api.data["hwver"])
        # Use translation key for entity name (translations in translations/*.json)
        self._attr_translation_key = key
        log_debug(
            _LOGGER,
            "__init__",
            "Switch initialized",
            device=self._coordinator.api.name,
            key=self._key,
        )

    async def async_force_update(self, delay: int = 0) -> None:
        """Force Switch State Update."""
        log_debug(
            _LOGGER,
            "async_force_update",
            "Coordinator forced update initiated",
            key=self._key,
        )
        if delay:
            await asyncio.sleep(delay)
        await self._coordinator.async_update_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._is_on = self._coordinator.api.data["relay_state"]
        self.async_write_ha_state()
        log_debug(
            _LOGGER,
            "_handle_coordinator_update",
            "Switch coordinator update requested",
            key=self._key,
        )

    @property
    def icon(self) -> str:
        """Return icon."""
        return self._icon

    @property
    def device_class(self) -> SwitchDeviceClass:
        """Return the switch device_class."""
        return self._device_class

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return the switch entity_category."""
        if self._device_class is SwitchDeviceClass.SWITCH:
            return EntityCategory.CONFIG
        return None

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{DOMAIN}_{self._device_sn}_{self._key}"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._is_on == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        set_response = await self._coordinator.api.telnet_set_relay("on")
        if set_response:
            log_debug(_LOGGER, "async_turn_on", "Switch turned on")
        else:
            log_debug(_LOGGER, "async_turn_on", "Error turning switch on")
        # call coord update for immediate refresh state
        self._handle_coordinator_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        set_response = await self._coordinator.api.telnet_set_relay("off")
        if set_response:
            log_debug(_LOGGER, "async_turn_off", "Switch turned off")
        else:
            log_debug(_LOGGER, "async_turn_off", "Error turning switch off")
        # call coord update for immediate refresh state
        self._handle_coordinator_update()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return DeviceInfo(
            hw_version=self._device_hwver,
            identifiers={(DOMAIN, self._device_sn)},
            manufacturer=self._device_manufact,
            model=self._device_model,
            name=self._device_name,
            serial_number=self._device_sn,
            sw_version=self._device_swver,
        )


class FebosHPRegisterSwitch(CoordinatorEntity[FebosHPCoordinator], SwitchEntity):
    """Switch backed by a Modbus register (via @REG 1 command)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FebosHPCoordinator,
        name: str,
        key: str,
        icon: str,
        device_class: SwitchDeviceClass,
        register: int,
    ) -> None:
        """Initialize the HP register switch."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._key = key
        self._icon = icon
        self._device_class = device_class
        self._register = register
        self._device_name: str = str(self._coordinator.api.name)
        self._device_host = self._coordinator.api.host
        self._device_model: str = str(self._coordinator.api.data["model"])
        self._device_manufact: str = str(self._coordinator.api.data["manufact"])
        self._device_sn: str = str(self._coordinator.api.data["sn"])
        self._device_swver: str = str(self._coordinator.api.data["swver"])
        self._device_hwver: str = str(self._coordinator.api.data["hwver"])
        self._attr_translation_key = key

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def icon(self) -> str:
        """Return icon."""
        return self._icon

    @property
    def device_class(self) -> SwitchDeviceClass:
        """Return the switch device_class."""
        return self._device_class

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return entity category."""
        return EntityCategory.CONFIG

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{DOMAIN}_{self._device_sn}_{self._key}"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._coordinator.api.data.get(self._key, 0) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        success = await self._coordinator.api.set_hp_register(self._register, 1)
        if success:
            self._coordinator.api.data[self._key] = 1
            log_debug(_LOGGER, "async_turn_on", "HP switch on", key=self._key)
        else:
            log_debug(_LOGGER, "async_turn_on", "HP switch on failed", key=self._key)
        self._handle_coordinator_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        success = await self._coordinator.api.set_hp_register(self._register, 0)
        if success:
            self._coordinator.api.data[self._key] = 0
            log_debug(_LOGGER, "async_turn_off", "HP switch off", key=self._key)
        else:
            log_debug(_LOGGER, "async_turn_off", "HP switch off failed", key=self._key)
        self._handle_coordinator_update()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return DeviceInfo(
            hw_version=self._device_hwver,
            identifiers={(DOMAIN, self._device_sn)},
            manufacturer=self._device_manufact,
            model=self._device_model,
            name=self._device_name,
            serial_number=self._device_sn,
            sw_version=self._device_swver,
        )


class FebosHPPauseSwitch(CoordinatorEntity[FebosHPCoordinator], SwitchEntity):
    """Switch to pause polling and free the TCP connection for the mobile app.

    ON = polling paused (connection released).
    OFF = polling active (normal operation).

    When turned on, auto-resumes after DEFAULT_PAUSE_DURATION seconds
    unless turned off manually first.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "pause_polling"

    def __init__(self, coordinator: FebosHPCoordinator) -> None:
        """Initialize the pause switch."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._device_name: str = str(self._coordinator.api.name)
        self._device_sn: str = str(self._coordinator.api.data["sn"])
        self._device_model: str = str(self._coordinator.api.data["model"])
        self._device_manufact: str = str(self._coordinator.api.data["manufact"])
        self._device_swver: str = str(self._coordinator.api.data["swver"])
        self._device_hwver: str = str(self._coordinator.api.data["hwver"])

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:pause-circle-outline" if self.is_on else "mdi:play-circle-outline"

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return entity category."""
        return EntityCategory.CONFIG

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{DOMAIN}_{self._device_sn}_pause_polling"

    @property
    def is_on(self) -> bool:
        """Return true if polling is paused."""
        return self._coordinator.is_paused

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Pause polling with auto-resume after DEFAULT_PAUSE_DURATION."""
        await self._coordinator.async_pause(duration=DEFAULT_PAUSE_DURATION)
        self.async_write_ha_state()
        log_debug(_LOGGER, "async_turn_on", "Polling paused (auto-resume in 5 min)")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Resume polling immediately."""
        await self._coordinator.async_resume()
        self.async_write_ha_state()
        log_debug(_LOGGER, "async_turn_off", "Polling resumed")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update — refresh switch state (auto-resume)."""
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return DeviceInfo(
            hw_version=self._device_hwver,
            identifiers={(DOMAIN, self._device_sn)},
            manufacturer=self._device_manufact,
            model=self._device_model,
            name=self._device_name,
            serial_number=self._device_sn,
            sw_version=self._device_swver,
        )
