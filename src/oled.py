# MIT License
# Copyright (c) 2020 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

from machine import Pin, I2C
import ssd1306
import textwrap

class OLED:

    def __init__(self, scl_pin = 22, sda_pin = 21, contrast = 127):
        self.i2c = I2C(-1, scl = Pin(scl_pin), sda = Pin(sda_pin))
        self.oled_width = 128
        self.oled_height = 64
        self.oled = ssd1306.SSD1306_I2C(self.oled_width, self.oled_height, self.i2c)
        self.oled.fill(0)
        self.oled.contrast(contrast)
        self.oled.text("      ...      ", 4, 30)
        self.oled.show()
        self.standby_x = 0
        self.standby_y = 0

    def show(self, artist, title, progress = None, ticks = True, separator = True):
        self.oled.fill(0)

        y = 0
        a = textwrap.wrap(artist, width = int(self.oled_width / 8), center = True)
        t = textwrap.wrap(title, width = int(self.oled_width / 8), center = True)

        if len(a) == 1 and len(a) + len(t) <= 4:
            y = 10

        for a_line in a:
            x = 0
            if len(a_line.strip()) % 2 == 1:
                x = 4
            self.oled.text(a_line, x, y)
            y = y + 10

        if len(a) + len(t) <= 5:
            spacing = 10
        else:
            spacing = 4

        y = y + spacing

        if progress is not None:
            if ticks:
                for i in range(self.oled_width):
                    if i % 32 == 0:
                        self.oled.pixel(i, y - int(spacing / 2) - 2, 1)
                        self.oled.pixel(i, y - int(spacing / 2) - 1, 1)
                self.oled.pixel(self.oled_width - 1, y - int(spacing / 2) - 2, 1)
                self.oled.pixel(self.oled_width - 1, y - int(spacing / 2) - 1, 1)

            if progress < 0:
                progress = 0
            if progress > 100:
                progress = 100

            barwidth = int(round(progress / 100 * self.oled_width, 0))

            for i in range(barwidth):
                self.oled.pixel(i, y - int(spacing / 2) - 2, 1)
                self.oled.pixel(i, y - int(spacing / 2) - 1, 1)
        else:
            if separator:
                for i in range(31, 95):
                    self.oled.pixel(i, y - int(spacing / 2) - 2, 1)
                    self.oled.pixel(i, y - int(spacing / 2) - 1, 1)

        for t_line in t:
            x = 0
            if len(t_line.strip()) % 2 == 1:
                x = 4
            self.oled.text(t_line, x, y)
            y = y + 10

        self.oled.show()

    def standby(self):
        self.oled.fill(0)
        self.oled.pixel(self.standby_x, self.standby_y, 1)
        self.oled.show()

        if self.standby_y == 0 and self.standby_x < self.oled_width - 1:
            self.standby_x += 1
        elif self.standby_x == self.oled_width - 1 and self.standby_y < self.oled_height - 1:
            self.standby_y += 1
        elif self.standby_y == self.oled_height - 1 and self.standby_x > 0:
            self.standby_x -= 1
        elif self.standby_x == 0 and self.standby_y > 0:
            self.standby_y -= 1

    def _corner_dot(self, fill, size = 1):
        for x in range(self.oled_width - size, self.oled_width):
            for y in range(size):
                self.oled.pixel(x, y, fill)

        self.oled.show()

    def show_corner_dot(self, size = 1):
        self._corner_dot(1, size = size)

    def hide_corner_dot(self, size = 1):
        self._corner_dot(0, size = size)

    def clear(self):
        self.oled.fill(0)
        self.oled.show()
