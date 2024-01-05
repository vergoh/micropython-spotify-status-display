# MIT License
# Copyright (c) 2020 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

from machine import Pin, SoftI2C
import ssd1306
import textutils

class OLED:

    def __init__(self, scl_pin = 22, sda_pin = 21, contrast = 127, enable = True):
        self.oled_width = 128
        self.oled_height = 64
        self.standby_x = 0
        self.standby_y = 0
        self.status_dot = False
        self.status_dot_size = 1

        if enable is False:
            self.enabled = False
            return

        self.i2c = SoftI2C(scl = Pin(scl_pin), sda = Pin(sda_pin))
        self.oled = ssd1306.SSD1306_I2C(self.oled_width, self.oled_height, self.i2c)
        self.oled.fill(0)
        self.oled.contrast(contrast)
        self.oled.text("      ...      ", 4, 30)
        self.oled.show()
        self.enabled = True

    def _replace_chars(self, text):
        result = []
        replaces = {192: 'A', 193: 'A', 194: 'A', 195: 'A', 196: 'A', 197: 'A', 198: 'A', 199: 'C', 200: 'E', 201: 'E', 202: 'E', 203: 'E', 204: 'I',
                    205: 'I', 206: 'I', 207: 'I', 208: 'D', 209: 'N', 210: 'O', 211: 'O', 212: 'O', 213: 'O', 214: 'O', 215: 'x', 216: 'O', 217: 'U',
                    218: 'U', 219: 'U', 220: 'U', 221: 'Y', 222: 'P', 223: 'B', 224: 'a', 225: 'a', 226: 'a', 227: 'a', 228: 'a', 229: 'a', 230: 'a',
                    231: 'c', 232: 'e', 233: 'e', 234: 'e', 235: 'e', 236: 'i', 237: 'i', 238: 'i', 239: 'i', 240: 'o', 241: 'n', 242: 'o', 243: 'o',
                    244: 'o', 245: 'o', 246: 'o', 247: '/', 248: 'o', 249: 'u', 250: 'u', 251: 'u', 252: 'u', 253: 'y', 254: 'p', 255: 'y', 256: 'A',
                    257: 'a', 258: 'A', 259: 'a', 260: 'A', 261: 'a', 262: 'C', 263: 'c', 264: 'C', 265: 'c', 266: 'C', 267: 'c', 268: 'C', 269: 'c',
                    270: 'D', 271: 'd', 272: 'D', 273: 'd', 274: 'E', 275: 'e', 276: 'E', 277: 'e', 278: 'E', 279: 'e', 280: 'E', 281: 'e', 282: 'E',
                    283: 'e', 284: 'G', 285: 'g', 286: 'G', 287: 'g', 288: 'G', 289: 'g', 290: 'G', 291: 'g', 292: 'H', 293: 'h', 294: 'H', 295: 'h',
                    296: 'I', 297: 'i', 298: 'I', 299: 'i', 300: 'I', 301: 'i', 302: 'I', 303: 'i', 304: 'I', 305: 'i', 306: 'I', 307: 'i', 308: 'J',
                    309: 'j', 310: 'K', 311: 'k', 312: 'k', 313: 'L', 314: 'l', 315: 'L', 316: 'l', 317: 'L', 318: 'l', 319: 'L', 320: 'l', 321: 'L',
                    322: 'l', 323: 'N', 324: 'n', 325: 'N', 326: 'n', 327: 'N', 328: 'n', 329: 'n', 330: 'N', 331: 'n', 332: 'O', 333: 'o', 334: 'O',
                    335: 'o', 336: 'O', 337: 'o',                     340: 'R', 341: 'r', 342: 'R', 343: 'r', 344: 'R', 345: 'r', 346: 'S', 347: 's',
                    348: 'S', 349: 's', 350: 'S', 351: 's', 352: 'S', 353: 's', 354: 'T', 355: 't', 356: 'T', 357: 't', 358: 'T', 359: 't', 360: 'U',
                    361: 'u', 362: 'U', 363: 'u', 364: 'U', 365: 'u', 366: 'U', 367: 'u', 368: 'U', 369: 'u', 370: 'U', 371: 'u', 372: 'W', 373: 'w',
                    374: 'Y', 375: 'y', 376: 'Y', 377: 'Z', 378: 'z', 379: 'Z', 380: 'z', 381: 'Z', 382: 'z'}

        for i in range(0, len(text)):
            c = ord(text[i])
            if 32 <= c <= 126:
                result.append(text[i])
            elif c in replaces:
                result.append(replaces[c])
            else:
                result.append('?')

        return ''.join(result)

    def show(self, artist, title, progress = None, ticks = True, separator = True):
        if not self.enabled:
            if progress is not None:
                print("Display: {} - {} ({}%)".format(artist.strip(), title.strip(), progress))
            else:
                print("Display: {} - {}".format(artist.strip(), title.strip()))
            return

        self.oled.fill(0)

        if self.status_dot:
            for x in range(self.status_dot_size):
                for y in range(self.status_dot_size):
                    self.oled.pixel(x, y, 1)

        y = 0
        a = textutils.wrap(self._replace_chars(artist.strip()), width = int(self.oled_width / 8), center = True)
        t = textutils.wrap(self._replace_chars(title.strip()), width = int(self.oled_width / 8), center = True)

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
        if not self.enabled:
            return

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
        if not self.enabled:
            return

        for x in range(self.oled_width - size, self.oled_width):
            for y in range(size):
                self.oled.pixel(x, y, fill)

        self.oled.show()

    def show_corner_dot(self, size = 1):
        self._corner_dot(1, size = size)

    def hide_corner_dot(self, size = 1):
        self._corner_dot(0, size = size)

    def enable_status_dot(self, size = 1):
        self.status_dot = True
        self.status_dot_size = size

    def disable_status_dot(self):
        self.status_dot = False

    def clear(self):
        if not self.enabled:
            return

        self.oled.fill(0)
        self.oled.show()
