# micropython-spotify-status-display

Micropython implementation for ESP32 using a small OLED display to show the "currently playing" information of a Spotify playback device. Optionally two buttons can be added for controlling the playback device. For normal usability, having the buttons is recommended.

## Features

- "currently playing" track shown with artist name and progress bar
- playback control
  - play/pause
  - next track
  - add current track to library
- configurable poll interval and behaviour
- access token stored in device after initial login
- screensaver for standby mode
- self contained implementation

## Requirements

- esp32 with [micropython](https://micropython.org/) 1.13 or later
- ssd1306 compatible 128x64 pixel display in i2c mode (0.91" oled tested)
- wlan connectivity
- Spotify account, Premium needed for playback control

## Limitations

- buttons don't react during api requests
- buttons require Spotify Premium due to api restrictions
- default font shows correctly mainly us-ascii characters
- playback device isn't aware of the status display resulting in delay status changes when the playback device is directly controlled

## TODO

- fix possible edge cases in api usage
- verify/implement support for 2.42" oled
- async api requests
- 3D printed case or other more permanent solution

## Getting started

### Wiring

Example connections for "ESP32 DevKit v1" and "Geekcreit 30 Pin" pins. Pins may vary on other ESP32 boards.

#### OLED

| ESP32 | OLED |
| --- | --- |
| 3V3 | VCC |
| GND | GND |
| D21 | SDA |
| D22 | SCK |

#### Buttons

| ESP32 | button | ESP32 |
| --- | --- | --- |
| D4 | left button | GND |
| D5 | right button | GND |

Button pins need to support internal pullups.

### Getting Spotify client_id and client_secret

1. Login do [Spotify developer dashboard](https://developer.spotify.com/dashboard/login)
2. Select "Create an app"
3. Fill "Status display" or similar as app name, description can be a link to this project or anything else
4. Click "Edit setting" and add `http://spostatus.local/callback/` as "Redirect URI"
   - `spostatus` needs to match the `mdns` name configured in the next section
   - `http://` prefix and `.local/callback/` must remain as shown
5. Save the settings dialog
6. Click "Show client secret" and take note of both "Client ID" and "Client Secret"

### src/config.json

1. Fill `client_id` and `client_secret` with values acquired in previous step
2. Fill `pins` section according to used wiring
3. Fill `wlan` section, use `mdns` value selected in previous step

### Final steps

1. Using a serial connection to micropython command line, `put` the content of `src` directory to the root of the device
2. Start `repl` and soft reset the device with ctrl-d
3. Fix any possible configuration errors based on shown output
4. Login to Spotify using the provided url and accept requested permissions

If a Spotify device doesn't currently have playback active then the display should reflect the situation. Start playback and the display should react to the change within the configured poll interval.

## Controls

Left button controls play/pause/resume with short presses. A long press (>= 500 ms by default) will result in the currently playing track to be saved to the user library (equivalent for pressing the heart symbol in the normal Spotify interface).

Right button requests the next track to be started.

Pressing either buttons during standby will wake up the display.

## Included 3rd party implementations

| file | description |
| --- | --- |
| `ssd1306.py` | <https://github.com/adafruit/micropython-adafruit-ssd1306> |
| `uurequests.py` | based on <https://github.com/pfalcon/pycopy-lib/blob/master/uurequests/uurequests.py> |
| `helpers.py` | reduced from <https://github.com/blainegarrett/urequests2> |
