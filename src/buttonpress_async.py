# MIT License
# Copyright (c) 2020 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

import time
import uasyncio as asyncio

DEBOUNCE = 30

class button_async():
    def __init__(self, buttonpin = None, long_press_duration_ms = 1000, buzzer = None):
        self.pin = buttonpin
        self.long_press_duration_ms = long_press_duration_ms
        self._buzzer = buzzer
        self._pressed = False
        self._was_pressed = False
        self._press_duration_ms = 0
        loop = asyncio.get_event_loop()
        loop.create_task(self.run())

    async def run(self):
        while True:
            if self.pin == None or self.pin.value() == 1:
                await asyncio.sleep_ms(10)
                continue

            press_start_time_ms = time.ticks_ms()

            self._pressed = True
            if self._buzzer is not None:
                self._buzzer.buzz()

            await asyncio.sleep_ms(DEBOUNCE)

            long_press_buzzed = False
            while self.pin.value() == 0:
                if self._buzzer is not None and long_press_buzzed is False and time.ticks_diff(time.ticks_ms(), press_start_time_ms) >= self.long_press_duration_ms:
                    self._buzzer.buzz()
                    long_press_buzzed = True
                await asyncio.sleep_ms(10)
            self._pressed = False
            self._press_duration_ms = time.ticks_diff(time.ticks_ms(), press_start_time_ms)

            await asyncio.sleep_ms(DEBOUNCE)

            self._was_pressed = True

    def was_pressed(self):
        if self._was_pressed:
            return True
        return False

    def was_longpressed(self):
        if self._was_pressed and self._press_duration_ms >= self.long_press_duration_ms:
            return True
        return False

    def reset_press(self):
        self._was_pressed = False
        self._press_duration_ms = 0

    async def wait_for_press(self):
        self.reset_press()
        while True:
            if self.was_pressed():
                self.reset_press()
                break
            else:
                await asyncio.sleep_ms(10)
