"""FEBOS room thermostat readings, in the controller's integer tenths of °C."""

from dataclasses import dataclass
from math import isfinite

AMBIENT = 8993
EFFECTIVE = 9085
COMPRESSOR_FREQUENCY = 9091
POWER = 16384
WINTER = 16385
NIGHT = 16386
ROOM_FLAG_KEYS = {POWER: "hp_onoff", WINTER: "hp_winter_mode", NIGHT: "hp_night_mode"}
COMFORT = 16440
ATTENUATION = 16442
MIN_COMFORT = 150
MAX_COMFORT = 300


@dataclass(frozen=True)
class RoomState:
    """A single poll of the live status and room settings."""

    power: int
    winter: int
    night: int
    ambient: int
    effective: int
    comfort: int
    attenuation: int
    compressor_frequency: int | None = None

    @classmethod
    def from_registers(
        cls, live: dict[str, str], settings: dict[str, str], *, changing_season: bool = False
    ) -> "RoomState":
        """Decode the raw replies, without using seeded or previously cached values."""
        try:
            compressor_frequency = int(live[str(COMPRESSOR_FREQUENCY)])
        except (KeyError, ValueError):
            compressor_frequency = None
        state = cls(
            power=int(live[str(POWER)]),
            winter=int(live[str(WINTER)]),
            night=int(live[str(NIGHT)]),
            ambient=int(live[str(AMBIENT)]),
            effective=int(live[str(EFFECTIVE)]),
            comfort=int(settings[str(COMFORT)]),
            attenuation=int(settings[str(ATTENUATION)]),
            compressor_frequency=compressor_frequency,
        )
        settings_season = int(settings.get(str(WINTER), state.winter))
        if (
            any(flag not in (0, 1) for flag in (state.power, state.winter, state.night))
            or settings_season not in (0, 1)
            or (not changing_season and settings_season != state.winter)
            or not MIN_COMFORT <= state.comfort <= MAX_COMFORT
            or not 10 <= state.attenuation <= 100
        ):
            raise ValueError("Invalid room control registers")
        return state

    @property
    def offset(self) -> int | None:
        """Return the observed offset only when both groups agree on the profile."""
        delta = self.effective - self.comfort
        if delta == 0 and not self.night:
            return 0
        if delta == (-self.attenuation if self.winter else self.attenuation):
            return delta
        return None

    def comfort_for_target(self, temperature: float, *, winter: bool | None = None) -> int:
        """Translate an effective target into a representable comfort register value."""
        offset = self.offset
        if offset is None:
            raise ValueError("The effective target does not match a known temperature profile")
        if not isfinite(temperature):
            raise ValueError("The target must be a finite temperature")
        if winter is not None and winter != bool(self.winter):
            offset = -offset
        comfort = round(temperature * 10) - offset
        if not MIN_COMFORT <= comfort <= MAX_COMFORT:
            raise ValueError(
                f"The effective target must be between {(MIN_COMFORT + offset) / 10:g} "
                f"and {(MAX_COMFORT + offset) / 10:g} °C for the active profile"
            )
        return comfort
