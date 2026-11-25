"""Exercise the FEBOS climate entity against in-memory gateway replies."""

import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import HVACAction
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.emmeti_feboshp.api import FebosHPAPI
from custom_components.emmeti_feboshp.climate import FebosHPRoomClimate
from custom_components.emmeti_feboshp.coordinator import FebosHPCoordinator
from custom_components.emmeti_feboshp.room import COMPRESSOR_FREQUENCY, NIGHT, POWER, ROOM_FLAG_KEYS, WINTER
from custom_components.emmeti_feboshp.switch import FebosHPRegisterSwitch


class RoomClimateTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.coordinator = MagicMock()
        self.coordinator.is_paused = False
        self.coordinator.schedule_room_readback = FebosHPCoordinator.schedule_room_readback.__get__(self.coordinator)
        self.coordinator._async_confirm_room = FebosHPCoordinator._async_confirm_room.__get__(self.coordinator)
        self.background_tasks = []
        self.coordinator.config_entry.async_create_background_task.side_effect = self.capture_task
        self.api = self.coordinator.api = FebosHPAPI(MagicMock(), "FEBOS", "example.invalid", 5001)
        self.api.connection_manager.execute = AsyncMock(side_effect=self.reply)
        self.coordinator.async_request_refresh = AsyncMock(side_effect=self.api.async_get_data)
        self.climate = FebosHPRoomClimate(self.coordinator)
        self.live = {16384: 1, 16385: 1, 16386: 0, 8993: 205, 9085: 210}
        self.settings = {16440: 220, 16442: 10}
        self.writes = []
        self.scheduled_attenuation = True
        self.ignore_write = False

    def capture_task(self, hass, coroutine, name):
        self.background_tasks.append(coroutine)
        self.addCleanup(coroutine.close)

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

    async def test_hvac_activity_uses_live_compressor_frequency(self):
        self.assertIsNone(self.climate.hvac_action)
        for season, mode, active in (
            (1, HVACMode.HEAT, HVACAction.HEATING),
            (0, HVACMode.COOL, HVACAction.COOLING),
        ):
            self.live[WINTER] = season
            for frequency, action in ((0, HVACAction.IDLE), (2, active), (1, HVACAction.IDLE)):
                with self.subTest(mode=mode, frequency=frequency):
                    self.live[COMPRESSOR_FREQUENCY] = frequency
                    await self.api.async_get_data()
                    self.assertEqual(self.climate.hvac_mode, mode)
                    self.assertEqual(self.climate.hvac_action, action)
        self.live[POWER] = 0
        self.live[COMPRESSOR_FREQUENCY] = 2
        await self.api.async_get_data()
        self.assertEqual(self.climate.hvac_action, HVACAction.OFF)
        self.assertEqual(self.writes, [])

    async def test_missing_or_malformed_frequency_clears_only_activity(self):
        self.live[COMPRESSOR_FREQUENCY] = 12
        await self.api.async_get_data()
        self.assertEqual(self.climate.hvac_action, HVACAction.HEATING)
        del self.live[COMPRESSOR_FREQUENCY]
        await self.api.async_get_data()
        self.assertIsNone(self.climate.hvac_action)
        self.live[COMPRESSOR_FREQUENCY] = "invalid"
        await self.api.async_get_data()
        self.assertIsNone(self.climate.hvac_action)
        self.assertEqual(self.climate.hvac_mode, HVACMode.HEAT)
        self.assertEqual(self.climate.native_target_temperature, 21)

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

    async def test_stale_snapshots_confirm_without_resending(self):
        # A late effective setpoint can temporarily equal the *new* comfort register.
        self.ignore_write = True
        await self.climate.async_set_temperature(temperature=20)
        await self.api.async_get_data()
        self.assertEqual(self.climate.native_target_temperature, 20)
        self.assertEqual(self.api.data["hp_ambient_setpoint"], 21)
        self.assertTrue(self.climate.extra_state_attributes["target_temperature_pending"])
        self.settings[16440] = 210
        await self.api.async_get_data()
        self.assertEqual(self.climate.native_target_temperature, 20)
        self.assertEqual(self.climate.extra_state_attributes["temperature_profile"], "eco")
        await self.climate.async_set_temperature(temperature=20)
        self.apply_profile()
        await self.api.async_get_data()
        self.assertFalse(self.climate.extra_state_attributes["target_temperature_pending"])
        self.assertEqual(self.climate.native_target_temperature, 20)
        self.assertEqual(self.writes, [(16440, 210)])

    async def test_latest_target_wins_while_effective_arrives_before_comfort(self):
        self.ignore_write = True
        await self.climate.async_set_temperature(temperature=22)
        self.live[9085] = 220
        await self.api.async_get_data()
        self.assertTrue(self.climate.extra_state_attributes["target_temperature_pending"])
        # Going back to the original target must override the first hardware command.
        await self.climate.async_set_temperature(temperature=21)
        self.settings[16440] = 230
        await self.api.async_get_data()
        self.assertEqual(self.climate.native_target_temperature, 21)
        self.settings[16440] = 220
        self.apply_profile()
        await self.api.async_get_data()
        self.assertFalse(self.climate.extra_state_attributes["target_temperature_pending"])
        self.assertEqual(self.writes, [(16440, 230), (16440, 220)])

    async def test_first_readback_confirms_after_two_seconds(self):
        await self.climate.async_set_temperature(temperature=22)
        self.assertTrue(self.climate.extra_state_attributes["target_temperature_pending"])
        self.api.connection_manager.execute.reset_mock()
        with patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
            await self.background_tasks[0]
        self.assertEqual([call.args[0] for call in sleep.await_args_list if call.args[0]], [2])
        self.assertEqual(
            [call.args[0] for call in self.api.connection_manager.execute.await_args_list],
            ["@DAM 1", "@DAM 2"],
        )
        self.assertFalse(self.climate.extra_state_attributes["target_temperature_pending"])
        self.assertEqual(self.writes, [(16440, 230)])

    async def test_unconfirmed_target_expires_after_three_readbacks(self):
        self.ignore_write = True
        elapsed = 0
        delays = []

        async def advance(delay):
            nonlocal elapsed
            if delay:
                delays.append(delay)
                elapsed += delay

        with patch("custom_components.emmeti_feboshp.api.monotonic", side_effect=lambda: elapsed):
            await self.climate.async_set_temperature(temperature=22)
            with (
                patch("asyncio.sleep", side_effect=advance),
                self.assertLogs("custom_components.emmeti_feboshp.api", level="WARNING"),
            ):
                await self.background_tasks[0]
        self.assertEqual(delays, [2, 2, 2])
        self.assertEqual(self.climate.native_target_temperature, 21)
        self.assertFalse(self.climate.extra_state_attributes["target_temperature_pending"])
        self.assertEqual(self.writes, [(16440, 230)])

    async def test_superseded_and_paused_readbacks_skip_gateway(self):
        self.ignore_write = True
        await self.climate.async_set_temperature(temperature=22)
        await self.climate.async_set_temperature(temperature=23)
        self.api.connection_manager.execute.reset_mock()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await self.background_tasks[0]
            self.coordinator.is_paused = True
            await self.background_tasks[1]
        self.api.connection_manager.execute.assert_not_awaited()

    async def test_external_adjustment_supersedes_pending_target(self):
        self.ignore_write = True
        await self.climate.async_set_temperature(temperature=22)
        self.settings[16440] = 240
        self.apply_profile()
        await self.api.async_get_data()
        self.assertFalse(self.climate.extra_state_attributes["target_temperature_pending"])
        self.assertEqual(self.climate.native_target_temperature, 23)
        self.assertEqual(self.writes, [(16440, 230)])

    async def test_gateway_rejection_does_not_change_target(self):
        async def reject_write(cmd):
            if cmd.startswith("@REG 1 "):
                return f"{cmd}\r\ncommand error\r\n\r\nready...\r\n"
            return await self.reply(cmd)

        self.api.connection_manager.execute.side_effect = reject_write
        with self.assertRaises(HomeAssistantError):
            await self.climate.async_set_temperature(temperature=22)
        self.assertFalse(self.climate.extra_state_attributes["target_temperature_pending"])
        self.assertEqual(self.climate.native_target_temperature, 21)

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

    async def test_each_room_flag_stays_visible_until_confirmed(self):
        self.ignore_write = True
        cases = [
            (self.climate.async_turn_off, (), POWER, 0, HVACMode.OFF, "schedule"),
            (self.climate.async_turn_on, (), POWER, 1, HVACMode.HEAT, "schedule"),
            (self.climate.async_set_hvac_mode, (HVACMode.COOL,), WINTER, 0, HVACMode.COOL, "schedule"),
            (self.climate.async_set_hvac_mode, (HVACMode.HEAT,), WINTER, 1, HVACMode.HEAT, "schedule"),
            (self.climate.async_set_preset_mode, ("sleep",), NIGHT, 1, HVACMode.HEAT, "sleep"),
            (self.climate.async_set_preset_mode, ("schedule",), NIGHT, 0, HVACMode.HEAT, "schedule"),
        ]
        for action, args, addr, value, mode, preset in cases:
            with self.subTest(addr=addr, value=value):
                self.writes.clear()
                await action(*args)
                await self.api.async_get_data()  # Both groups still contain the old values.
                self.assertEqual(self.climate.hvac_mode, mode)
                self.assertEqual(self.climate.preset_mode, preset)
                self.assertEqual(self.api.data[ROOM_FLAG_KEYS[addr]], value)
                self.assertIn(addr, self.api.pending_room_flags)
                await action(*args)  # Identical request while the first is in flight.
                self.live[addr] = value
                self.apply_profile()
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    await self.background_tasks[-1]
                self.assertEqual(self.api.pending_room_flags, {})
                self.assertEqual(self.writes, [(addr, value)])

    async def test_partial_mode_confirmation_expires_per_register(self):
        self.live[POWER] = 0
        self.ignore_write = True
        elapsed = 0

        async def advance(delay):
            nonlocal elapsed
            elapsed += delay
            if elapsed >= 2:
                self.live[POWER] = 1

        with patch("custom_components.emmeti_feboshp.api.monotonic", side_effect=lambda: elapsed):
            await self.climate.async_set_hvac_mode(HVACMode.COOL)
            self.assertEqual(self.climate.hvac_mode, HVACMode.COOL)
            with (
                patch("asyncio.sleep", side_effect=advance),
                self.assertLogs("custom_components.emmeti_feboshp.api", level="WARNING") as logs,
            ):
                await self.background_tasks[0]
        self.assertEqual(elapsed, 6)
        self.assertEqual(len(logs.records), 1)
        self.assertIn(str(WINTER), logs.output[0])
        self.assertEqual(self.api.pending_room_flags, {})
        self.assertEqual(self.climate.hvac_mode, HVACMode.HEAT)
        self.assertEqual(self.writes, [(WINTER, 0), (POWER, 1)])

    async def test_switch_supersedes_climate_while_night_is_pending(self):
        self.ignore_write = True
        await self.api.async_get_data()
        switch = FebosHPRegisterSwitch(self.coordinator, "Night", ROOM_FLAG_KEYS[NIGHT], "", None, NIGHT)
        await self.climate.async_set_preset_mode("sleep")
        await switch.async_turn_off()
        self.live[NIGHT] = 1  # Late echo of the first command.
        await self.api.async_get_data()
        self.assertEqual(self.climate.preset_mode, "schedule")
        self.assertFalse(switch.is_on)
        self.api.connection_manager.execute.reset_mock()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await self.background_tasks[0]
            self.api.connection_manager.execute.assert_not_awaited()
            self.live[NIGHT] = 0
            await self.background_tasks[1]
        self.assertEqual(self.writes, [(NIGHT, 1), (NIGHT, 0)])
        self.assertEqual(self.api.pending_room_flags, {})

    async def test_combined_temperature_waits_for_both_season_snapshots(self):
        self.settings[WINTER] = 1
        self.ignore_write = True
        waits = []

        async def update_registers(delay):
            if delay:
                waits.append(delay)
                self.assertEqual(self.writes, [(WINTER, 0)])
                self.live[WINTER] = 0
                if len(waits) == 2:
                    self.settings[WINTER] = 0
                    self.apply_profile()

        with patch("asyncio.sleep", side_effect=update_registers):
            await self.climate.async_set_temperature(hvac_mode=HVACMode.COOL, temperature=22)
        self.assertEqual(waits, [2, 2])
        self.assertEqual(self.writes, [(WINTER, 0), (16440, 210)])
        self.assertEqual(self.climate.native_target_temperature, 22)

    async def test_failed_power_write_still_reconciles_accepted_season(self):
        self.live[POWER] = 0
        self.ignore_write = True

        async def reject_power(cmd):
            if cmd == f"@REG 1 {POWER} 1 1":
                return f"{cmd}\r\ncommand error\r\n\r\nready...\r\n"
            return await self.reply(cmd)

        self.api.connection_manager.execute.side_effect = reject_power
        with self.assertRaisesRegex(HomeAssistantError, str(POWER)):
            await self.climate.async_set_hvac_mode(HVACMode.COOL)
        self.assertEqual(self.climate.hvac_mode, HVACMode.OFF)
        self.assertEqual(set(self.api.pending_room_flags), {WINTER})
        self.live[WINTER] = 0
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await self.background_tasks[0]
        self.assertEqual(self.api.pending_room_flags, {})

    async def test_unconfirmed_season_skips_dependent_temperature_write(self):
        self.ignore_write = True
        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            self.assertRaises(HomeAssistantError),
        ):
            await self.climate.async_set_temperature(hvac_mode=HVACMode.COOL, temperature=22)
        self.assertEqual(self.writes, [(WINTER, 0)])
