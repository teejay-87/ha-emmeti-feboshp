"""Exercise the FEBOS climate entity against in-memory gateway replies."""

import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.climate import HVACMode
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.emmeti_feboshp.api import FebosHPAPI
from custom_components.emmeti_feboshp.climate import FebosHPRoomClimate
from custom_components.emmeti_feboshp.switch import FebosHPRegisterSwitch


class RoomClimateTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.coordinator = MagicMock()
        self.coordinator.is_paused = False
        self.api = self.coordinator.api = FebosHPAPI(MagicMock(), "FEBOS", "example.invalid", 5001)
        self.api.connection_manager.execute = AsyncMock(side_effect=self.reply)
        self.coordinator.async_request_refresh = AsyncMock(side_effect=self.api.async_get_data)
        self.climate = FebosHPRoomClimate(self.coordinator)
        self.live = {16384: 1, 16385: 1, 16386: 0, 8993: 205, 9085: 210}
        self.settings = {16440: 220, 16442: 10}
        self.writes = []
        self.scheduled_attenuation = True
        self.ignore_write = False

    async def reply(self, cmd):
        await asyncio.sleep(0)  # Let concurrent service calls interleave if the lock is missing.
        if cmd.startswith("@REG 1 "):
            _, _, address, value, _ = cmd.split()
            address, value = int(address), int(value)
            self.writes.append((address, value))
            if not self.ignore_write:
                registers = self.settings if address == 16440 else self.live
                registers[address] = value
                self.apply_profile()
        registers = {"@DAM 1": self.live, "@DAM 2": self.settings}.get(cmd, {})
        rows = [f"{i};{key};{value};0" for i, (key, value) in enumerate(registers.items())]
        return "\r\n".join([cmd, *rows, "", "ready...", ""])

    def apply_profile(self):
        sign = -1 if self.live[16385] else 1
        attenuated = self.scheduled_attenuation or self.live[16386]
        self.live[9085] = self.settings[16440] + (sign * self.settings[16442] if attenuated else 0)

    async def test_winter_setback_and_morning(self):
        await self.api.async_get_data()
        self.assertEqual(self.writes, [])
        self.assertEqual(self.climate.native_current_temperature, 20.5)
        self.assertEqual(self.climate.native_target_temperature, 21)
        self.assertEqual((self.climate.min_temp, self.climate.max_temp), (14, 29))
        await self.climate.async_set_temperature(temperature=22)
        self.assertEqual(self.writes, [(16440, 230)])
        self.assertEqual(self.climate.native_target_temperature, 22)
        self.scheduled_attenuation = False
        self.apply_profile()
        await self.api.async_get_data()
        self.assertEqual(self.climate.native_target_temperature, 23)
        self.assertEqual(self.climate.extra_state_attributes["temperature_profile"], "comfort")
        self.assertEqual(self.writes, [(16440, 230)])
        await self.climate.async_set_temperature(temperature=22)
        self.assertEqual(self.writes[-1], (16440, 220))

    async def test_summer_and_limits(self):
        self.live[16385] = 0
        self.apply_profile()
        await self.climate.async_set_temperature(temperature=22.4)
        self.assertEqual(self.writes, [(16440, 214)])
        self.assertEqual(self.climate.native_target_temperature, 22.4)
        self.assertEqual((self.climate.min_temp, self.climate.max_temp), (16, 31))
        with self.assertRaises(ServiceValidationError):
            await self.climate.async_set_temperature(temperature=15.5)
        self.assertEqual(self.writes, [(16440, 214)])

    async def test_sleep_and_release_during_scheduled_setback(self):
        await self.api.async_get_data()
        await self.climate.async_set_preset_mode("sleep")
        self.assertEqual(self.climate.preset_mode, "sleep")
        self.assertEqual(self.api.data["hp_night_mode"], 1)
        self.assertEqual(self.climate.extra_state_attributes["temperature_profile"], "sleep")
        switch = FebosHPRegisterSwitch(self.coordinator, "Night", "hp_night_mode", "", None, 16386)
        switch.async_write_ha_state = MagicMock()
        self.assertTrue(switch.is_on)
        await switch.async_turn_off()
        self.assertEqual(self.climate.preset_mode, "schedule")
        self.assertEqual(self.climate.extra_state_attributes["temperature_profile"], "eco")
        self.assertEqual(self.climate.native_target_temperature, 21)
        self.assertEqual(self.writes, [(16386, 1), (16386, 0)])

    async def test_invalid_data_and_pause_do_not_write(self):
        await self.api.async_get_data()
        self.settings.clear()
        await self.api.async_get_data()
        self.assertIsNone(self.api.room)
        self.assertEqual(self.api.data["hp_ambient_temp"], 20.5)
        with self.assertRaises(HomeAssistantError):
            await self.climate.async_set_temperature(temperature=22)
        self.settings.update({16440: 220, 16442: 10})
        self.live[9085] = 215
        with self.assertRaises(ServiceValidationError):
            await self.climate.async_set_temperature(temperature=22)
        self.assertIsNone(self.climate.extra_state_attributes["temperature_profile"])
        self.coordinator.is_paused = True
        self.api.connection_manager.execute.reset_mock()
        with self.assertRaises(HomeAssistantError):
            await self.climate.async_set_preset_mode("sleep")
        self.api.connection_manager.execute.assert_not_called()
        self.assertEqual(self.writes, [])

    async def test_write_requires_confirmation(self):
        self.ignore_write = True
        with self.assertRaises(HomeAssistantError):
            await self.climate.async_set_temperature(temperature=22)
        self.assertEqual(self.climate.native_target_temperature, 21)
        self.assertEqual(self.writes, [(16440, 230)])

    async def test_concurrent_changes_use_new_profile(self):
        self.scheduled_attenuation = False
        self.apply_profile()
        await asyncio.gather(
            self.climate.async_set_preset_mode("sleep"),
            self.climate.async_set_temperature(temperature=22),
        )
        self.assertEqual(self.writes, [(16386, 1), (16440, 230)])
        self.assertEqual(self.climate.native_target_temperature, 22)

    async def test_combined_mode_and_temperature(self):
        self.live[16384] = 0
        with self.assertRaises(ServiceValidationError):
            await self.climate.async_set_temperature(hvac_mode=HVACMode.COOL, temperature=15)
        self.assertEqual(self.writes, [])
        await self.climate.async_set_temperature(hvac_mode=HVACMode.COOL, temperature=22)
        self.assertEqual(self.writes, [(16385, 0), (16384, 1), (16440, 210)])
        self.assertEqual(self.climate.hvac_mode, HVACMode.COOL)
        await self.climate.async_turn_off()
        await self.climate.async_turn_on()
        self.assertEqual(self.writes[-2:], [(16384, 0), (16384, 1)])
        self.assertEqual(self.climate.hvac_mode, HVACMode.COOL)
