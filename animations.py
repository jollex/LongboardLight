from bibliopixel.led import *
from bibliopixel.drivers.LPD8806 import *
from bibliopixel.animation import BaseStripAnim
from adxl345 import ADXL345
import sys, signal, time, os, threading
import RPi.GPIO as GPIO

NUM_LEDS=24
RAINBOW=[colors.Red,\
         colors.Orange,\
         colors.Yellow,\
         colors.Green,\
         colors.Blue,\
         colors.Indigo]
MY_COLORS= [(209, 54, 68),\
            (239, 180, 110),\
            (254, 255, 238),\
            (73, 178, 161),\
            (53, 85, 108),\
            (93, 81, 215)]
TRICOLOR=  [(239,65,53),
            (255, 255, 255),
            (0, 85, 164)]
THRESHOLD = 8

#ANIMATIONS = [
#    ('StaticColorsAnim', 1, [colors.Black]),
#    ('GradiantAnim', 200, MY_COLORS),
#    ('StaticColorsAnim', 1, [colors.White]),
#    ('ColorStepperAnim', 4, MY_COLORS),
#    ('ColorStepperAnim', 3, TRICOLOR),
#    ('StaticColorsAnim', 1, [colors.Red, colors.Green, colors.Green, colors.Red]),
#    ('RotationAnim', 24, RAINBOW),
#    ('BetterAccelerationAnim', 200, [colors.Red, colors.Green])]
ANIMATIONS = [
    ('StaticColorsAnim', 1, [colors.Black]),
    ('GradiantAnim', 12, MY_COLORS),
    ('StaticColorsAnim', 1, [colors.White])]

class AccelerationAnim(BaseStripAnim):
    def __init__(self, led, start=0, end=-1):
        super(AccelerationAnim, self).__init__(led, start, end)
        self.color = colors.Red

    def step(self, amt=1):
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


def wait_for_button_press():
    prev_input = 0
    while True:
        input = GPIO.input(22)
        if (not prev_input) and input:
            return
        prev_input = input

def run_anims(led):
    i = 0
    while True:
        animDesc = ANIMATIONS[i % len(ANIMATIONS)]
        constructor = globals()[animDesc[0]]
        if (len(animDesc) > 2):
            anim = constructor(led, animDesc[2])
        else:
            anim = constructor(led)
        anim.run(fps=animDesc[1], threaded=True)
        wait_for_button_press()
        time.sleep(.5)
        anim.stopThread()
        i += 1

def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(22, GPIO.OUT)

    global adxl345
    adxl345 = ADXL345()

    driver = DriverLPD8806(NUM_LEDS, c_order=ChannelOrder.GRB)
    led = LEDStrip(driver)

    run_anims(led)

if __name__ == '__main__':
    main()
