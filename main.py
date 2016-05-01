################################################################################
# IMPORTS

from bibliopixel import colors
from bibliopixel.led import LEDStrip
from bibliopixel.drivers.driver_base import ChannelOrder
from bibliopixel.drivers.LPD8806 import DriverLPD8806
from bibliopixel.animation import BaseStripAnim

from adxl345 import ADXL345

import RPi.GPIO as GPIO

import argparse, sys, signal, time, os, threading

################################################################################
# DATA DEFINITIONS

# An Animation is a [String, Integer, [Color, ...]]
# Interpretation: The String is the name of a class inheriting from the
# BaseStripAnim class, the Integer is the FPS to run the animation at, and the
# list of Colors is a list of any colors that the animation takes in.

################################################################################
# CONSTANTS

# colors
RAINBOW=[colors.Red,
         colors.Orange,
         colors.Yellow,
         colors.Green,
         colors.Blue,
         colors.Indigo]
MY_COLORS= [(209, 54, 68),
            (239, 180, 110),
            (254, 255, 238),
            (73, 178, 161),
            (53, 85, 108),
            (93, 81, 215)]
TRICOLOR=  [(239,65,53),
            (255, 255, 255),
            (0, 85, 164)]

# misc
BUTTON_GPIO_PORT = 22

# number of LEDs
SKATE_LEDS=20
ROOM_LEDS=24
NUM_LEDS=SKATE_LEDS

# animation lists
SKATE = [
    ('StaticColorsAnim', 1, [colors.Black]),
    ('GradiantAnim', 200, MY_COLORS),
    ('StaticColorsAnim', 1, [colors.White]),
    ('ColorStepperAnim', 4, MY_COLORS),
    ('ColorStepperAnim', 3, TRICOLOR),
    ('StaticColorsAnim', 1,
        [colors.Red, colors.Green, colors.Green, colors.Red]),
    ('RotationAnim', 24, RAINBOW),
    ('BetterAccelerationAnim', 200, [colors.Red, colors.Green])]
ROOM = [
    ('StaticColorsAnim', 1, [colors.Black]),
    ('GradiantAnim', 12, MY_COLORS),
    ('StaticColorsAnim', 1, [colors.White])]

ANIMATION_LISTS = {'ROOM':  ROOM,
                   'SKATE': SKATE}

DEFAULT_ANIMATION = 'ROOM'

################################################################################
# ANIMATIONS

class AccelerationAnim(BaseStripAnim):
    def __init__(self, led, colors, start=0, end=-1):
        super(AccelerationAnim, self).__init__(led, start, end)
        self.color = colors.Red

    def step(self, amt=1):
        THRESHOLD = 8

        axes = adxl345.getAxes(False)

        if abs(axes['y']) < THRESHOLD:
            self.color = colors.Red
        else:
            self.color = colors.Green

        self._led.fill(self.color)

class BetterAccelerationAnim(BaseStripAnim):
    def __init__(self, led, colors, start=0, end=-1):
        super(BetterAccelerationAnim, self).__init__(led, start, end)
        self.low_color, self.high_color = colors
        self.min_accel, self.max_accel = 0, 0

    def get_y_accel(self):
        return adxl345.getAxes(False)['y']

    def step(self, amt=1):
        accel = self.get_y_accel()
        self.update_min_max_accel(accel)

        range = self.max_accel - self.min_accel or 1
        ratio = float(accel) / float(range)
        new_color = map(lambda low, high: BetterAccelerationAnim.get_average_value(low, high, ratio),
                        self.low_color,
                        self.high_color)

        self._led.fill(tuple(new_color))

    @staticmethod
    def get_average_value(low, high, ratio):
        difference = abs(low - high)
        interval = difference * ratio

        return int(min(low, high) + interval)

    def update_min_max_accel(self, accel):
        self.min_accel = min(self.min_accel, accel)
        self.max_accel = max(self.max_accel, accel)


class ColorStepperAnim(BaseStripAnim):
    def __init__(self, led, colors, start=0, end=-1):
        super(ColorStepperAnim, self).__init__(led, start, end)
        self._colors = colors

    def step(self, amt=1):
        self._led.fill(self._colors[self._step % len(self._colors)])
        self._step += amt

class RotationAnim(BaseStripAnim):
    def __init__(self, led, colors, start=0, end=-1):
        super(RotationAnim, self).__init__(led, start, end)
        self._colors = []
        for color in colors:
            self._colors += [color]*3

    def step(self, amt=1):
        for i in range(self._led.numLEDs):
            self._led.set(i, self._colors[(self._step + i) % len(self._colors)])

        self._step += amt

class GradiantAnim(BaseStripAnim):
    def __init__(self, led, colors, start=0, end=-1):
        super(GradiantAnim, self).__init__(led, start, end)
        self._colors = colors
        self._current = 0
        self._currentColor = self._colors[self._current]

    def step(self, amt=1):
        cur = self._currentColor
        next = self._colors[(self._current + 1) % len(self._colors)]
        self._currentColor = (self.increment(cur[0], next[0]),\
            self.increment(cur[1], next[1]),\
            self.increment(cur[2], next[2]))
        if self._currentColor == next:
            self._current = (self._current + 1) % len(self._colors)
        self._led.fill(self._currentColor)

    def increment(self, i1, i2):
        if i1 < i2:
            return i1 + 1
        elif i1 > i2:
            return i1 - 1
        else:
            return i1

class StaticColorsAnim(BaseStripAnim):
    def __init__(self, led, colors, start=0, end=-1):
        super(StaticColorsAnim, self).__init__(led, start, end)
        self._colors = colors

    def step(self, amt=1):
        ledsPerSection = self._led.numLEDs / len(self._colors)
        for i in range(len(self._colors)):
            for j in range(ledsPerSection):
                self._led.set((i * ledsPerSection) + j, self._colors[i])

################################################################################
# Main

def wait_for_button_press():
    """
    Loops forever until a button press is detected on BUTTON_GPIO_PORT
    """
    prev_input = 0
    while True:
        input = GPIO.input(BUTTON_GPIO_PORT)
        if (not prev_input) and input:
            return
        prev_input = input

def run_anims(animations, led):
    """
    Runs the given animations using the LEDStrip led

    :param animations: A list of Animations
    :param led: The LEDStrip to run animations on
    """
    i = 0
    while True:
        constructor, fps, colors = animations[i]

        animation_instance = globals()[constructor](led, colors)
        animation_instance.run(fps=fps, threaded=True)

        wait_for_button_press()
        time.sleep(.5)

        animation_instance.stopThread()

        i = (i + 1) % len(animations)

def main():
    """
    Main function, runs forever, running one Animation at a time from
    ANIMATIONS, switching to the next animation whenever a button press is
    received on BUTTON_GPIO_PORT
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'animations',
        choices=ANIMATION_LISTS.keys(),
        default=DEFAULT_ANIMATION,
        type=str,
        help='The list of animations to run, one of {}'.format(
            ANIMATION_LISTS.keys()))
    parser.add_argument(
        'num_leds',
        default=DEFAULT_NUM_LEDS,
        type=int,
        help='The number of leds on the LED strip being used')
    args = parser.parse_args()

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_GPIO_PORT, GPIO.OUT)

    global adxl345
    adxl345 = ADXL345()

    driver = DriverLPD8806(args.num_leds, c_order=ChannelOrder.GRB)
    led = LEDStrip(driver)

    run_anims(ANIMATION_LISTS[args.animations], led)

if __name__ == '__main__':
    main()
