from spi_driver_base import DriverSPIBase, ChannelOrder
import os
from .. import gamma


class DriverWS2801(DriverSPIBase):
    """Main driver for WS2801 based LED strips on devices like the Raspberry Pi and BeagleBone"""

    def __init__(self, num, c_order=ChannelOrder.RGB, use_py_spi=True, dev="/dev/spidev0.0", SPISpeed=1):
        if SPISpeed > 1 or SPISpeed <= 0:
            raise ValueError(
                "WS2801 requires an SPI speed no greater than 1MHz or SPI speed was set <= 0")
        super(DriverWS2801, self).__init__(num, c_order=c_order,
                                           use_py_spi=use_py_spi, dev=dev, SPISpeed=SPISpeed)

        self.gamma = gamma.WS2801

    # WS2801 requires gamma correction so we run it through gamma as the
    # channels are ordered
    def _fixData(self, data):
        for a, b in enumerate(self.c_order):
            self._buf[a:self.numLEDs * 3:3] = [self.gamma[v]
                                               for v in data[b::3]]

MANIFEST = [
    {
        "id": "WS2801",
        "class": DriverWS2801,
        "type": "driver",
        "display": "WS2801 (SPI Native)",
        "desc": "Interface with WS2801 strips over a native SPI port (Pi, BeagleBone, etc.)",
        "params": [{
                "id": "num",
                "label": "# Pixels",
                "type": "int",
                "default": 1,
                "min": 1,
                "help": "Total pixels in display."
        }, {
            "id": "c_order",
            "label": "Channel Order",
            "type": "combo",
            "options": {
                    0: "RGB",
                    1: "RBG",
                    2: "GRB",
                    3: "GBR",
                    4: "BRG",
                    5: "BGR"
            },
            "options_map": [
                [0, 1, 2],
                [0, 2, 1],
                [1, 0, 2],
                [1, 2, 0],
                [2, 0, 1],
                [2, 1, 0]
            ],
            "default": 0
        }, {
            "id": "dev",
            "label": "SPI Device Path",
            "type": "str",
            "default": "/dev/spidev0.0",
        }, {
            "id": "use_py_spi",
            "label": "Use PySPI",
            "type": "bool",
            "default": True,
            "group": "Advanced"
        }]
    }
]
