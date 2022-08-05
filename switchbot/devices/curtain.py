"""Library to handle connection with Switchbot."""
from __future__ import annotations

import logging
from typing import Any

from .device import SwitchbotDevice

# Curtain keys
OPEN_KEY = "570f450105ff00"  # 570F4501010100
CLOSE_KEY = "570f450105ff64"  # 570F4501010164
POSITION_KEY = "570F450105ff"  # +actual_position ex: 570F450105ff32 for 50%
STOP_KEY = "570F450100ff"
CURTAIN_EXT_SUM_KEY = "570f460401"
CURTAIN_EXT_ADV_KEY = "570f460402"
CURTAIN_EXT_CHAIN_INFO_KEY = "570f468101"


_LOGGER = logging.getLogger(__name__)


class SwitchbotCurtain(SwitchbotDevice):
    """Representation of a Switchbot Curtain."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Switchbot Curtain/WoCurtain constructor."""

        # The position of the curtain is saved returned with 0 = open and 100 = closed.
        # This is independent of the calibration of the curtain bot (Open left to right/
        # Open right to left/Open from the middle).
        # The parameter 'reverse_mode' reverse these values,
        # if 'reverse_mode' = True, position = 0 equals close
        # and position = 100 equals open. The parameter is default set to True so that
        # the definition of position is the same as in Home Assistant.

        super().__init__(*args, **kwargs)
        self._reverse: bool = kwargs.pop("reverse_mode", True)
        self._settings: dict[str, Any] = {}
        self.ext_info_sum: dict[str, Any] = {}
        self.ext_info_adv: dict[str, Any] = {}

    async def open(self) -> bool:
        """Send open command."""
        result = await self._sendcommand(OPEN_KEY, self._retry_count)
        if result[0] == 1:
            return True

        return False

    async def close(self) -> bool:
        """Send close command."""
        result = await self._sendcommand(CLOSE_KEY, self._retry_count)
        if result[0] == 1:
            return True

        return False

    async def stop(self) -> bool:
        """Send stop command to device."""
        result = await self._sendcommand(STOP_KEY, self._retry_count)
        if result[0] == 1:
            return True

        return False

    async def set_position(self, position: int) -> bool:
        """Send position command (0-100) to device."""
        position = (100 - position) if self._reverse else position
        hex_position = "%0.2X" % position
        result = await self._sendcommand(POSITION_KEY + hex_position, self._retry_count)
        if result[0] == 1:
            return True

        return False

    async def update(self, interface: int | None = None) -> None:
        """Update position, battery percent and light level of device."""
        await self.get_device_data(retry=self._retry_count, interface=interface)

    def get_position(self) -> Any:
        """Return cached position (0-100) of Curtain."""
        # To get actual position call update() first.
        return self._get_adv_value("position")

    async def get_basic_info(self) -> dict[str, Any] | None:
        """Get device basic settings."""
        if not (_data := await self._get_basic_info()):
            return None

        _position = max(min(_data[6], 100), 0)
        return {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "chainLength": _data[3],
            "openDirection": (
                "right_to_left" if _data[4] & 0b10000000 == 128 else "left_to_right"
            ),
            "touchToOpen": bool(_data[4] & 0b01000000),
            "light": bool(_data[4] & 0b00100000),
            "fault": bool(_data[4] & 0b00001000),
            "solarPanel": bool(_data[5] & 0b00001000),
            "calibrated": bool(_data[5] & 0b00000100),
            "inMotion": bool(_data[5] & 0b01000011),
            "position": (100 - _position) if self._reverse else _position,
            "timers": _data[7],
        }

    async def get_extended_info_summary(self) -> dict[str, Any] | None:
        """Get basic info for all devices in chain."""
        _data = await self._sendcommand(
            key=CURTAIN_EXT_SUM_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessfull, please try again")
            return None

        self.ext_info_sum["device0"] = {
            "openDirectionDefault": not bool(_data[1] & 0b10000000),
            "touchToOpen": bool(_data[1] & 0b01000000),
            "light": bool(_data[1] & 0b00100000),
            "openDirection": (
                "left_to_right" if _data[1] & 0b00010000 == 1 else "right_to_left"
            ),
        }

        # if grouped curtain device present.
        if _data[2] != 0:
            self.ext_info_sum["device1"] = {
                "openDirectionDefault": not bool(_data[1] & 0b10000000),
                "touchToOpen": bool(_data[1] & 0b01000000),
                "light": bool(_data[1] & 0b00100000),
                "openDirection": (
                    "left_to_right" if _data[1] & 0b00010000 else "right_to_left"
                ),
            }

        return self.ext_info_sum

    async def get_extended_info_adv(self) -> dict[str, Any] | None:
        """Get advance page info for device chain."""

        _data = await self._sendcommand(
            key=CURTAIN_EXT_ADV_KEY, retry=self._retry_count
        )

        if _data in (b"\x07", b"\x00"):
            _LOGGER.error("Unsuccessfull, please try again")
            return None

        _state_of_charge = [
            "not_charging",
            "charging_by_adapter",
            "charging_by_solar",
            "fully_charged",
            "solar_not_charging",
            "charging_error",
        ]

        self.ext_info_adv["device0"] = {
            "battery": _data[1],
            "firmware": _data[2] / 10.0,
            "stateOfCharge": _state_of_charge[_data[3]],
        }

        # If grouped curtain device present.
        if _data[4]:
            self.ext_info_adv["device1"] = {
                "battery": _data[4],
                "firmware": _data[5] / 10.0,
                "stateOfCharge": _state_of_charge[_data[6]],
            }

        return self.ext_info_adv

    def get_light_level(self) -> Any:
        """Return cached light level."""
        # To get actual light level call update() first.
        return self._get_adv_value("lightLevel")

    def is_reversed(self) -> bool:
        """Return True if curtain position is opposite from SB data."""
        return self._reverse

    def is_calibrated(self) -> Any:
        """Return True curtain is calibrated."""
        # To get actual light level call update() first.
        return self._get_adv_value("calibration")
