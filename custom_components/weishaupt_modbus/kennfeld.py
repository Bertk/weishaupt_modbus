"""Heat pump characteristic curves (Kennfeld)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiofiles  # type: ignore[import-untyped]
import numpy as np
from numpy.polynomial import Chebyshev

from homeassistant.core import HomeAssistant

from .configentry import MyConfigEntry
from .const import CONF, CONST

_LOGGER = logging.getLogger(__name__)

SPLINE_AVAILABLE = True
CubicSpline: Any = None
try:
    import scipy  # type: ignore[import-untyped] # noqa: F401 pylint: disable=unused-import
    from scipy.interpolate import CubicSpline  # type: ignore[import-untyped]

    _LOGGER.info(
        "Scipy available, use precise cubic spline interpolation for heating power"
    )
except ModuleNotFoundError:
    _LOGGER.warning(
        "Scipy not available, use less precise Chebyshef interpolation for heating power"
    )
    SPLINE_AVAILABLE = False

MATPLOTLIB_AVAILABLE = True
plt: Any = None
try:
    import matplotlib.pyplot as plt  # type: ignore[import-not-found,import-untyped]
except ModuleNotFoundError:
    _LOGGER.warning("Matplotlib not available. Can't create power map image file")
    MATPLOTLIB_AVAILABLE = False


class PowerMap:
    """Power map class."""

    # these are values extracted from the characteristic curves of heating power found ion the documentation of my heat pump.
    # there are two diagrams:
    #  - heating power vs. outside temperature @ 35 °C flow temperature
    #  - heating power vs. outside temperature @ 55 °C flow temperature
    known_x = [-30, -25, -22, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40]
    # known power values read out from the graphs plotted in documentation. Only 35 °C and 55 °C available
    known_y = [
        [
            5700,
            5700,
            5700,
            5700,
            6290,
            7580,
            8660,
            9625,
            10300,
            10580,
            10750,
            10790,
            10830,
            11000,
            11000,
            11000,
        ],
        [
            5700,
            5700,
            5700,
            5700,
            6860,
            7300,
            8150,
            9500,
            10300,
            10580,
            10750,
            10790,
            10830,
            11000,
            11000,
            11000,
        ],
    ]

    # the known x values for linear interpolation
    known_t = [35, 55]

    # the aim is generating a 2D power map that gives back the actual power for a certain flow temperature and a given outside temperature
    # the map should have values on every integer temperature point
    # at first, all flow temperatures are linearly interpolated

    def __init__(self, config_entry: MyConfigEntry, hass: HomeAssistant) -> None:
        """Initialize the PowerMap class."""
        self.hass = hass
        self._config_entry = config_entry
        self._steps = 21
        self._max_power: list[Any] = []
        self._interp_y: list[Any] = []
        self._r_to_interpolate: Any = None
        self._all_t: Any = None

    async def initialize(self) -> None:
        """Initialize the power map."""
        filepath = Path(
            get_filepath(self.hass) / self._config_entry.data[CONF.KENNFELD_FILE]
        )

        try:
            async with aiofiles.open(filepath, encoding="utf-8") as openfile:
                raw_block = await openfile.read()
                json_object = json.loads(raw_block)
                self.known_x = json_object["known_x"]
                self.known_y = json_object["known_y"]
                self.known_t = json_object["known_t"]
                _LOGGER.info("Reading power map file %s successful", filepath)
        except OSError:
            kennfeld = {
                "known_x": self.known_x,
                "known_y": self.known_y,
                "known_t": self.known_t,
            }
            async with aiofiles.open(filepath, "w", encoding="utf-8") as outfile:
                raw_block = json.dumps(kennfeld)
                await outfile.write(raw_block)
                _LOGGER.info(
                    "Writing power map file %s with generic content successful",
                    filepath,
                )

        self._r_to_interpolate = np.linspace(
            self.known_t[0], self.known_t[1], self._steps
        )
        # the output matrix
        self._max_power = []
        self._interp_y = []

        # build the matrix with linear interpolated samples
        # 1st and last row are populated by known values from diagram, the rest is zero
        self._interp_y.append(self.known_y[0])
        v = np.linspace(0, self._steps - 3, self._steps - 2)
        for _idx in v:
            self._interp_y.append(np.zeros_like(self.known_x))
        self._interp_y.append(self.known_y[1])

        for idx in range(len(self.known_x)):
            # the known y for every column
            yk = [self._interp_y[0][idx], self._interp_y[self._steps - 1][idx]]

            # linear interpolation
            ip = np.interp(self._r_to_interpolate, self.known_t, yk)

            # sort the interpolated values into the array
            for r in range(len(self._r_to_interpolate)):
                self._interp_y[r][idx] = ip[r]

        # at second step, power vs. outside temp are interpolated using cubic splines
        # we want to have samples at every integer °C
        self._all_t = np.linspace(-30, 40, 71)
        # cubic spline interpolation of power curves
        for idx in range(len(self._r_to_interpolate)):
            if SPLINE_AVAILABLE is True and CubicSpline is not None:
                f: Any = CubicSpline(
                    self.known_x, self._interp_y[idx], bc_type="natural"
                )
            else:
                f = Chebyshev.fit(self.known_x, self._interp_y[idx], deg=8)
            self._max_power.append(f(self._all_t))

        try:
            if MATPLOTLIB_AVAILABLE:
                await self._config_entry.runtime_data.hass.async_add_executor_job(
                    self.plot_kennfeld_to_file
                )
        except RuntimeError:
            _LOGGER.warning("Reconfigure powermap")

    def map(self, x: float, y: float) -> float:
        """Map temperature values to power."""
        x = x / 10 - self.known_x[0]
        x = max(x, 0)
        x = min(x, 70)
        y = y / 10 - self.known_t[0]
        y = max(y, 0)
        y = min(y, self._steps - 1)

        return self._max_power[int(y)][int(x)]

    def plot_kennfeld_to_file(self) -> None:
        """Plot the kennfeld file into png image for display."""
        if not MATPLOTLIB_AVAILABLE or plt is None:
            _LOGGER.warning("Matplotlib not available, cannot plot kennfeld")
            return

        plt.plot(self._all_t, np.transpose(self._max_power))
        plt.ylabel("Max Power")
        plt.xlabel("°C")
        plt.grid()
        plt.xlim(-25, 40)
        plt.ylim(2000, 12000)

        filepath = (
            self._config_entry.runtime_data.config_dir
            + "/www/local/"
            + CONST.DOMAIN
            + "_powermap.png"
        )

        try:
            plt.savefig(filepath)
            _LOGGER.info(
                "Write power map image file %s",
                filepath,
            )
        except OSError:
            _LOGGER.warning(
                "Error writing power map image file %s",
                filepath,
            )


def get_filepath(hass: HomeAssistant) -> Path | None:
    """Get the filepath to the custom component directory."""
    filepath = Path(f"{hass.config.config_dir}/custom_components/{CONST.DOMAIN}")

    # on some installations custom_components resides in /core/
    if not filepath.exists():
        filepath = Path(Path(__file__).resolve().parent)

    # we do not find any path..
    if not filepath.exists():
        return None
    return filepath
