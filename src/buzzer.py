# MIT License
# Copyright (c) 2022 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

import time
from machine import PWM

class buzzer():
    def __init__(self, buzzerpin = None, frequency = 2000, duty = 512):
        self._pin = buzzerpin
        self._frequency = frequency
        self._duty = duty
        self._pwm = None

        if self._pin is not None:
            self._pwm = PWM(self._pin)
            self._pwm.freq(self._frequency)
            self._pwm.duty(0)
            time.sleep_ms(100)

    def buzz(self, duration_ms = 25):
        if self._pwm is not None:
            self._pwm.duty(self._duty)
            time.sleep_ms(duration_ms)
            self._pwm.duty(0)
