# MIT License
# Copyright (c) 2020 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

import time
import ujson
import network
import uasyncio as asyncio
from machine import Pin

# imports from additional files
import oled
import spotify_api
from buttonpress_async import button_async

class Spotify:

    def __init__(self):
        self.name = "Spotify status"
        self.device_id = None

        self.config = {}
        with open('config.json', 'r') as f:
            self.config = ujson.load(f)

        if self.config['use_led']:
            self.led = Pin(self.config['pins']['led'], Pin.OUT)
            for v in [1, 0, 1]:
                self.led.value(v)
                time.sleep_ms(100)
            self.led.value(0)

        self.oled = oled.OLED(scl_pin = self.config['pins']['scl'], sda_pin = self.config['pins']['sda'])
        self.oled.show(self.name, "__init__", separator = False)

        self._validate_config()

        if not self.config['spotify'].get('client_id') or not self.config['spotify'].get('client_secret'):
            self.oled.show(self.name, "client not configured", separator = False)
            raise RuntimeError("client_id and/or client_secret not configured")

        if self.config['use_buttons']:
            self.button_playpause = button_async(Pin(self.config['pins']['button_playpause'], Pin.IN, Pin.PULL_UP), long_press_duration_ms = self.config['long_press_duration_milliseconds'])
            self.button_next = button_async(Pin(self.config['pins']['button_next'], Pin.IN, Pin.PULL_UP), long_press_duration_ms = self.config['long_press_duration_milliseconds'])
            print("buttons enabled")
        else:
            print("buttons disabled")

        if self.config['setup_network']:
            self.wlan_ap = network.WLAN(network.AP_IF)
            self.wlan_ap.active(False)
            self.wlan = network.WLAN(network.STA_IF)
            self.wlan.active(True)
            self.wlan.connect(self.config['wlan']['ssid'], self.config['wlan']['password'])
            self.wlan.config(dhcp_hostname=self.config['wlan']['mdns'])
            print("network configured")
        else:
            self.wlan = network.WLAN()
            print("using existing network configuration")

        if self.config['enable_webrepl']:
            import webrepl
            webrepl.start()

        while not self.wlan.isconnected():
            self.oled.show(self.name, "waiting for connection", separator = False)
            time.sleep_ms(500)
            self.oled.show(self.name, "waiting for connection", separator = True)
            time.sleep_ms(500)

        self.ip = self.wlan.ifconfig()[0]
        self.redirect_uri = "http://{}.local/callback/".format(self.config['wlan']['mdns'])

        self.oled.show(self.name, "__init__ connected {}".format(self.ip), separator = False)
        print("Connected at {} as {}".format(self.ip, self.config['wlan']['mdns']))

    def _validate_config(self):
        boolean_entries = ['use_led', 'use_buttons', 'setup_network', 'enable_webrepl', 'show_progress_ticks']
        integer_entries = ['status_poll_interval_seconds', 'idle_standby_minutes', 'long_press_duration_milliseconds', 'api_request_dot_size']
        dict_entries = ['spotify', 'pins', 'wlan']
        spotify_entries = ['client_id', 'client_secret']
        pin_entries = ['led', 'scl', 'sda', 'button_playpause', 'button_next']
        wlan_entries = ['ssid', 'password', 'mdns']

        for b in boolean_entries:
            if b not in self.config or type(self.config[b]) is not bool:
                self._raise_config_error("\"{}\" not configured or not boolean".format(b))

        for i in integer_entries:
            if i not in self.config or type(self.config[i]) is not int:
                self._raise_config_error("\"{}\" not configured or not integer".format(i))

        for d in dict_entries:
            if d not in self.config or type(self.config[d]) is not dict:
                self._raise_config_error("\"{}\" not configured or not dict".format(d))

        for s in spotify_entries:
            if s not in self.config['spotify'] or self.config['spotify'][s] is None or len(self.config['spotify'][s]) < 16:
                self._raise_config_error("\"{}\" not configured or is invalid".format(s))

        for p in pin_entries:
            if p not in self.config['pins'] or type(self.config['pins'][p]) is not int:
                self._raise_config_error("\"{}\" not configured or is invalid".format(p))

        for w in wlan_entries:
            if w not in self.config['wlan'] or self.config['wlan'][w] is None or len(self.config['wlan'][w]) < 1:
                self._raise_config_error("\"{}\" not configured or is invalid".format(w))

    def _raise_config_error(self, e):
        self.oled.show("config.json", e)
        raise RuntimeError(e)

    def _reset_button_presses(self):
        if self.config['use_buttons']:
            self.button_playpause.reset_press()
            self.button_next.reset_press()

    def _check_button_presses(self):
        if self.config['use_buttons']:
            if self.button_playpause.was_pressed() or self.button_next.was_pressed():
                return True
        return False

    def _handle_buttons(self, api_tokens, playing):
        if not self._check_button_presses():
            return

        if self.button_playpause.was_pressed():
            print("play/pause button pressed")
            if playing:
                if self.button_playpause.was_longpressed():
                    self.oled.show(self.name, "saving track", separator = False)
                    currently_playing = self._get_currently_playing(api_tokens)
                    if currently_playing is not None:
                        if 'item' in currently_playing and 'id' in currently_playing['item']:
                            self._save_track(api_tokens, currently_playing['item'].get('id'))
                else:
                    self.oled.show(self.name, "pausing playback", separator = False)
                    self.device_id = self._get_current_device_id(api_tokens)
                    self._pause_playback(api_tokens)
            else:
                self.oled.show(self.name, "resuming playback", separator = False)
                self._resume_playback(api_tokens, self.device_id)

        elif self.button_next.was_pressed():
            print("next button pressed")
            self.oled.show(self.name, "requesting next", separator = False)
            if playing:
                self._next_playback(api_tokens)
            else:
                self._next_playback(api_tokens, self.device_id)

        self._reset_button_presses()

    def _validate_api_reply(self, api_call_name, api_reply, ok_status_list = [], warn_status_list = [], raise_status_list = [], warn_duration_ms = 3000):
        if api_reply['status_code'] in ok_status_list:
            return True

        if api_reply['status_code'] in warn_status_list:
            warning_text = "{} api {}: {}".format(api_call_name, r['status_code'], r['text'])
            print(warning_text)
            self.oled.show(self.name, warning_text, separator = False)
            time.sleep_ms(warn_duration_ms)
            return False

        if len(raise_status_list) == 0 or api_reply['status_code'] in raise_status_list:
            self.oled.show(self.name, "{} api error {}".format(api_call_name, r['status_code']), separator = False)
            raise RuntimeError("Error {} - {}".format(r['status_code'], r['text']))

        self.oled.show(self.name, "{} api unhandled error {}".format(api_call_name, r['status_code']), separator = False)
        raise RuntimeError("Error unhandled status_code {} - {}".format(r['status_code'], r['text']))

    def _get_api_tokens(self, authorization_code):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.get_api_tokens(authorization_code, self.redirect_uri, self.config['spotify']['client_id'], self.config['spotify']['client_secret'])
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("token", r, ok_status_list = [200])

        print("api tokens received")
        api_tokens = r['json']

        print("received: {}".format(api_tokens))
        api_tokens['timestamp'] = time.time()

        if 'refresh_token' in api_tokens:
            with open('refresh_token.txt', 'w') as f:
                f.write(api_tokens['refresh_token'])
            print("refresh_token.txt created")

        return api_tokens

    def _refresh_access_token(self, api_tokens):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.refresh_access_token(api_tokens, self.config['spotify']['client_id'], self.config['spotify']['client_secret'])
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("refresh", r, ok_status_list = [200])

        print("refreshed api tokens received")
        new_api_tokens = r['json']

        print("received: {}".format(new_api_tokens))
        new_api_tokens['timestamp'] = time.time()

        if 'refresh_token' in new_api_tokens:
            if new_api_tokens['refresh_token'] != api_tokens['refresh_token']:
                with open('refresh_token.txt', 'w') as f:
                    f.write(new_api_tokens['refresh_token'])
                print("refresh_token.txt updated")
        else:
            new_api_tokens['refresh_token'] = api_tokens['refresh_token']

        return new_api_tokens

    def _get_currently_playing(self, api_tokens):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.get_currently_playing(api_tokens)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("playback", r, ok_status_list = [200, 204], warn_status_list = [401, 403, 429])

        print("playback status received")

        if r['status_code'] == 200:
            currently_playing = r['json']
        else:
            currently_playing = None

        if currently_playing is not None:
            if 'is_playing' not in currently_playing or currently_playing['is_playing'] is not True or 'item' not in currently_playing:
                currently_playing = None

        return currently_playing

    def _get_current_device_id(self, api_tokens):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.get_current_device_id(api_tokens)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("player", r, ok_status_list = [200], warn_status_list = [401, 403, 429])

        print("player received")

        player_status = r['json']

        device_id = None
        if 'device' in player_status:
            if 'id' in player_status['device']:
                if player_status['device']['id'] is not None and len(player_status['device']['id']) > 8:
                    device_id = player_status['device']['id']
                    print("current device id: {}".format(device_id))

        return device_id

    def _pause_playback(self, api_tokens):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.pause_playback(api_tokens)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("pause", r, ok_status_list = [204], warn_status_list = [401, 403, 429])

        print("playback paused")

    def _resume_playback(self, api_tokens, device_id = None):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.resume_playback(api_tokens, device_id = device_id)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("resume", r, ok_status_list = [204, 404])

        if r['status_code'] == 404:
            print("no active device found")
            self.oled.show(self.name, "no active device found", separator = False)
            time.sleep(3)
        else:
            print("playback resuming")

    def _next_playback(self, api_tokens, device_id = None):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.next_playback(api_tokens, device_id = device_id)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("next", r, ok_status_list = [204, 404], warn_status_list = [401, 403, 429])

        if r['status_code'] == 404:
            print("no active device found")
            self.oled.show(self.name, "no active device found", separator = False)
            time.sleep(3)
        else:
            print("playback next")

    def _save_track(self, api_tokens, track_id):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.save_track(api_tokens, track_id)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("save track", r, ok_status_list = [200], warn_status_list = [401, 403, 429])

        print("track saved")

    def _initial_token_request(self):
        self.oled.show("Login", "http:// {}.local".format(self.config['wlan']['mdns']), separator = False)
        authorization_code = spotify_api.get_authorization_code(self.config['spotify']['client_id'], self.redirect_uri, self.ip, self.config['wlan']['mdns'])

        if authorization_code == None:
            self.oled.show(self.name, "get_auth_code() failed", separator = False)
            raise RuntimeError("get_auth_code() failed")

        self.oled.show(self.name, "authorized", separator = False)
        print("authorization_code content: {}".format(authorization_code))

        api_tokens = self._get_api_tokens(authorization_code)

        return api_tokens

    async def _show_play_progress_for_seconds(self, cp, seconds):
        if 'progress_ms' not in cp or 'duration_ms' not in cp['item']:
            self.oled.show(cp['item'].get('artists', [{}])[0].get('name'), cp['item'].get('name'))
            await asyncio.sleep(seconds)
        else:
            progress_start = time.time()
            progress = None

            if 'progress_ms' in cp and 'duration_ms' in cp['item']:
                progress_ms = cp['progress_ms']
                progress = True

            while True:
                interval_begins = time.ticks_ms()

                if progress is not None:
                    if progress_ms > cp['item']['duration_ms']:
                        break
                    progress = int(round(progress_ms / float(cp['item']['duration_ms']) * 100, 0))

                self.oled.show(cp['item'].get('artists', [{}])[0].get('name'), cp['item'].get('name'), progress = progress, ticks = self.config['show_progress_ticks'])
                if time.time() >= progress_start + seconds:
                    break

                if await self._wait_for_button_press_ms(1000):
                    break

                progress_ms += time.ticks_ms() - interval_begins

    async def _wait_for_button_press_ms(self, milliseconds):
        interval_begins = time.ticks_ms()
        button_pressed = self._check_button_presses()

        while not button_pressed and time.ticks_ms() - interval_begins < milliseconds:
            await asyncio.sleep_ms(50)
            button_pressed = self._check_button_presses()

        if button_pressed:
            return True
        else:
            return False

    async def _standby(self):
        print("standby")
        self._reset_button_presses()
        button_pressed = self._check_button_presses()

        while not button_pressed:
            self.oled.standby()
            button_pressed = await self._wait_for_button_press_ms(10 * 1000)

        self._reset_button_presses()
        self.oled.show(self.name, "resuming operations", separator = False)

    async def _looper(self):
        self.oled.show("Spotify status", "start", separator = False)

        api_tokens = None

        try:
            refresh_token_file = open('refresh_token.txt', 'r')
        except OSError:
            refresh_token_file = None

        if refresh_token_file is None:
            api_tokens = self._initial_token_request()
        else:
            refresh_token = refresh_token_file.readline().strip()
            refresh_token_file.close()
            api_tokens = self._refresh_access_token({ 'refresh_token': refresh_token })

        self.oled.show(self.name, "tokenized", separator = False)
        print("api_tokens content: {}".format(api_tokens))

        playing = False
        last_playing = time.time()
        self._reset_button_presses()

        while True:
            if time.time() >= api_tokens['timestamp'] + api_tokens['expires_in'] - 30:
                api_tokens = self._refresh_access_token(api_tokens)

            self._handle_buttons(api_tokens, playing)

            currently_playing = self._get_currently_playing(api_tokens)

            if currently_playing is not None:
                playing = True
                last_playing = time.time()
                if self.device_id is None:
                    self.device_id = self._get_current_device_id(api_tokens)
            else:
                playing = False

            if playing:
                await self._show_play_progress_for_seconds(currently_playing, self.config['status_poll_interval_seconds'])
            else:
                self.oled.show("Spotify", "not playing", separator = False)

                if time.time() >= last_playing + self.config['idle_standby_minutes'] * 60:
                    if self.config['use_buttons']:
                        await self._standby()
                        last_playing = time.time()
                        continue
                    else:
                        self.oled.clear()
                        print("stopping due to inactivity")
                        break

                await self._wait_for_button_press_ms(self.config['status_poll_interval_seconds'] * 1000)

        print("Loop ended")

    def start(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self._looper())
        except KeyboardInterrupt:
            print("keyboard interrupt received, stopping")
            self.oled.clear()
