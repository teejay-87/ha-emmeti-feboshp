"""Effective room temperature control for the FEBOS heat pump."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_SLEEP,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FebosHPConfigEntry
from .api import ROOM_TARGET_CHECK_ATTEMPTS, ROOM_TARGET_CHECK_INTERVAL, PendingRoomTarget
from .connection_manager import ConnectionManagerError
from .const import DOMAIN
from .coordinator import FebosHPCoordinator
from .room import COMFORT, MAX_COMFORT, MIN_COMFORT, NIGHT, POWER, WINTER, RoomState

PRESET_SCHEDULE = "schedule"


async def async_setup_entry(
    hass: HomeAssistant, entry: FebosHPConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Register the thermostat, including when optional room data is temporarily missing."""
    async_add_entities([FebosHPRoomClimate(entry.runtime_data.coordinator)])


class FebosHPRoomClimate(CoordinatorEntity[FebosHPCoordinator], ClimateEntity):
    """A thermostat whose dial always represents the controller's effective target."""

    _attr_has_entity_name = True
    _attr_translation_key = "room"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.1
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_preset_modes = [PRESET_SCHEDULE, PRESET_SLEEP]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE |
        ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
    )

    def __init__(self, coordinator: FebosHPCoordinator) -> None:
        super().__init__(coordinator)
        self.api = coordinator.api
        serial = str(self.api.data["sn"])
        self._attr_unique_id = f"{DOMAIN}_{serial}_room"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial)})

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.is_paused and self.api.room is not None

    @property
    def hvac_mode(self) -> HVACMode | None:
        if (room := self.api.room) is None:
            return None
        if not room.power:
            return HVACMode.OFF
        return HVACMode.HEAT if room.winter else HVACMode.COOL

    @property
    def native_current_temperature(self) -> float | None:
        return room.ambient / 10 if (room := self.api.room) else None

    @property
    def native_target_temperature(self) -> float | None:
        return room.effective / 10 if (room := self.api.room_for_control) else None

    # Home Assistant versions before the native temperature API (including 2024.12).
    if not hasattr(ClimateEntity, "native_target_temperature"):
        _attr_temperature_unit = UnitOfTemperature.CELSIUS
        current_temperature = native_current_temperature
        target_temperature = native_target_temperature

    @property
    def min_temp(self) -> float:
        room = self.api.room_for_control
        return (MIN_COMFORT + (room.offset or 0)) / 10 if room else MIN_COMFORT / 10

    @property
    def max_temp(self) -> float:
        room = self.api.room_for_control
        return (MAX_COMFORT + (room.offset or 0)) / 10 if room else MAX_COMFORT / 10

    @property
    def preset_mode(self) -> str | None:
        if (room := self.api.room) is None:
            return None
        return PRESET_SLEEP if room.night else PRESET_SCHEDULE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if (room := self.api.room) is None:
            return {}
        offset = (self.api.room_for_control or room).offset
        profile = None
        if offset == 0:
            profile = PRESET_COMFORT
        elif offset is not None:
            profile = PRESET_SLEEP if room.night else PRESET_ECO
        return {
            "target_temperature_pending": self.api.pending_room_target is not None,
            "temperature_profile": profile,
            "comfort_temperature_c": room.comfort / 10,
            "attenuation_c": room.attenuation / 10,
        }

    async def _read_room(self) -> RoomState:
        await self.api.read_hp_data()
        if (room := self.api.room_for_control) is None:
            raise HomeAssistantError("Room control registers are unavailable")
        return room

    @asynccontextmanager
    async def _command(self) -> AsyncIterator[RoomState]:
        """Use fresh readings and serialize the full operation with HP switches and polling."""
        async with self.api.hp_lock:
            if self.coordinator.is_paused:
                raise HomeAssistantError("FEBOS polling is paused")
            try:
                yield await self._read_room()
            finally:
                self.coordinator.async_update_listeners()

    async def _set_register(self, address: int, field: str, value: int, room: RoomState) -> RoomState:
        """Send an absolute value and verify the register through the normal read path."""
        if getattr(room, field) == value:
            return room
        if self.coordinator.is_paused:
            raise HomeAssistantError("FEBOS polling is paused")
        if not await self.api.set_hp_register(address, value):
            raise HomeAssistantError(f"FEBOS could not write register {address}")
        room = await self._read_room()
        if getattr(room, field) == value:
            return room
        # The gateway can acknowledge before its DAM snapshot reflects the write.
        await asyncio.sleep(0.5)
        room = await self._read_room()
        if getattr(room, field) == value:
            return room
        raise HomeAssistantError(f"FEBOS did not confirm register {address}")

    async def _set_mode(self, mode: HVACMode, room: RoomState) -> RoomState:
        if mode not in self.hvac_modes:
            raise ServiceValidationError(f"Unsupported HVAC mode: {mode}")
        if mode != HVACMode.OFF:
            room = await self._set_register(WINTER, "winter", int(mode == HVACMode.HEAT), room)
        return await self._set_register(POWER, "power", int(mode != HVACMode.OFF), room)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        async with self._command() as room:
            await self._set_mode(hvac_mode, room)

    async def async_turn_on(self) -> None:
        async with self._command() as room:
            await self._set_register(POWER, "power", 1, room)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in self._attr_preset_modes:
            raise ServiceValidationError(f"Unsupported preset: {preset_mode}")
        async with self._command() as room:
            await self._set_register(NIGHT, "night", int(preset_mode == PRESET_SLEEP), room)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        async with self._command() as room:
            mode = kwargs.get(ATTR_HVAC_MODE)
            temperature = kwargs[ATTR_TEMPERATURE]
            try:
                if mode is not None:
                    # Validate the combined request before making any change to the plant.
                    winter = mode == HVACMode.HEAT if mode != HVACMode.OFF else None
                    room.comfort_for_target(temperature, winter=winter)
                    room = await self._set_mode(mode, room)
                comfort = room.comfort_for_target(temperature)
            except ValueError as err:
                raise ServiceValidationError(str(err)) from err
            if self.coordinator.is_paused:
                raise HomeAssistantError("FEBOS polling is paused")
            previous = self.api.pending_room_target
            if not await self.api.set_room_comfort(room, comfort):
                raise HomeAssistantError(f"FEBOS could not write register {COMFORT}")
            pending = self.api.pending_room_target
            if pending is not None and pending is not previous:
                self.coordinator.config_entry.async_create_background_task(
                    self.coordinator.hass, self._async_confirm_target(pending), "FEBOS target readback"
                )

    async def _async_confirm_target(self, pending: PendingRoomTarget) -> None:
        """Read only the HP groups until this particular write is reconciled."""
        for _ in range(ROOM_TARGET_CHECK_ATTEMPTS):
            await asyncio.sleep(ROOM_TARGET_CHECK_INTERVAL)
            async with self.api.hp_lock:
                if self.api.pending_room_target is not pending or self.coordinator.is_paused:
                    return
                try:
                    await self.api.read_hp_data()
                except ConnectionManagerError:
                    # A read failure leaves the room unavailable. Normal polling handles recovery.
                    return
                finally:
                    self.coordinator.async_update_listeners()
                if self.api.pending_room_target is not pending:
                    return
