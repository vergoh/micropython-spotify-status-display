# MIT License
# Copyright (c) 2020 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

import gc
import time
import ujson
import network
import uasyncio as asyncio
from machine import Pin
from micropython import const, mem_info

# imports from additional files
import oled
import spotify_api
from buttonpress_async import button_async
from buzzer import buzzer

_app_name = const("Spotify status")

class Spotify:

    def __init__(self):
        self.device_id = None
        self.pause_after_current = False
        self._set_memory_debug()
        self.config = {}
        with open('config.json', 'r') as f:
            self.config = ujson.load(f)

        if self.config['use_led']:
            self.led = Pin(self.config['pins']['led'], Pin.OUT)
            for v in [1, 0, 1]:
                self.led.value(v)
                time.sleep_ms(100)
            self.led.value(0)

        if self.config['use_display']:
            self.oled = oled.OLED(scl_pin = self.config['pins']['scl'], sda_pin = self.config['pins']['sda'], contrast = self.config['contrast'])
            if self.config['low_contrast_mode']:
                self.oled.oled.precharge(0x22)
        else:
            self.oled = oled.OLED(enable = False)
        self.oled.show(_app_name, "__init__", separator = False)

        self._validate_config()

        if self.config['use_buzzer']:
            self.buzzer = buzzer(Pin(self.config['pins']['buzzer'], Pin.OUT), frequency = self.config['buzzer_frequency'], duty = self.config['buzzer_duty'])
            self.buzzer.buzz()
        else:
            self.buzzer = None

        if not self.config['spotify'].get('client_id') or not self.config['spotify'].get('client_secret'):
            self.oled.show(_app_name, "client not configured", separator = False)
            raise RuntimeError("client_id and/or client_secret not configured")

        self.button_playpause = button_async(Pin(self.config['pins']['button_playpause'], Pin.IN, Pin.PULL_UP), long_press_duration_ms = self.config['long_press_duration_milliseconds'], buzzer = self.buzzer)
        self.button_next = button_async(Pin(self.config['pins']['button_next'], Pin.IN, Pin.PULL_UP), long_press_duration_ms = self.config['long_press_duration_milliseconds'], buzzer = self.buzzer)
        print("buttons enabled")

        if self.config['setup_network']:
            self.wlan_ap = network.WLAN(network.AP_IF)
            self.wlan_ap.active(False)
            self.wlan = network.WLAN(network.STA_IF)
            try:
                self.wlan.active(True)
                self.wlan.connect(self.config['wlan']['ssid'], self.config['wlan']['password'])
                self.wlan.config(dhcp_hostname=self.config['wlan']['mdns'])
            except Exception as e:
                self.oled.show(e.__class__.__name__, str(e))
                if str(e) == "Wifi Internal Error":
                    time.sleep(3)
                    import machine
                    machine.reset()
                else:
                    raise
            print("network configured")
        else:
            self.wlan = network.WLAN()
            print("using existing network configuration")

        if self.config['enable_webrepl']:
            import webrepl
            webrepl.start()

        self._wait_for_connection()

        self.ip = self.wlan.ifconfig()[0]
        self.redirect_uri = "http://{}.local/callback/".format(self.config['wlan']['mdns'])

        self.oled.show(_app_name, "__init__ connected {}".format(self.ip), separator = False)
        print("connected at {} as {}".format(self.ip, self.config['wlan']['mdns']))

    def _set_memory_debug(self):
        import os
        self.memdebug = False

        try:
            if os.stat("memdebug") != 0:
                self.memdebug = True
        except Exception:
            pass

        if self.memdebug:
            print("memory debug enabled")
        else:
            print("no \"memdebug\" file or directory found, memory debug output disabled")

    def _validate_config(self):
        boolean_entries = const("use_display,use_led,use_buzzer,setup_network,enable_webrepl,show_progress_ticks,low_contrast_mode,blank_oled_on_standby")
        integer_entries = const("contrast,status_poll_interval_seconds,standby_status_poll_interval_minutes,idle_standby_minutes,long_press_duration_milliseconds,api_request_dot_size,buzzer_frequency,buzzer_duty")
        dict_entries = const("spotify,pins,wlan")
        spotify_entries = const("client_id,client_secret")
        pin_entries = const("led,scl,sda,button_playpause,button_next,buzzer")
        wlan_entries = const("ssid,password,mdns")

        for b in boolean_entries.split(','):
            if b not in self.config or type(self.config[b]) is not bool:
                self._raise_config_error("\"{}\" not configured or not boolean".format(b))

        for i in integer_entries.split(','):
            if i not in self.config or type(self.config[i]) is not int:
                self._raise_config_error("\"{}\" not configured or not integer".format(i))

        for d in dict_entries.split(','):
            if d not in self.config or type(self.config[d]) is not dict:
                self._raise_config_error("\"{}\" not configured or not dict".format(d))

        for s in spotify_entries.split(','):
            if s not in self.config['spotify'] or self.config['spotify'][s] is None or len(self.config['spotify'][s]) < 16:
                self._raise_config_error("\"{}\" not configured or is invalid".format(s))

        for p in pin_entries.split(','):
            if p not in self.config['pins'] or type(self.config['pins'][p]) is not int:
                self._raise_config_error("\"{}\" not configured or is invalid".format(p))

        for w in wlan_entries.split(','):
            if w not in self.config['wlan'] or self.config['wlan'][w] is None or len(self.config['wlan'][w]) < 1:
                self._raise_config_error("\"{}\" not configured or is invalid".format(w))

    def _raise_config_error(self, e):
        self.oled.show("config.json", e)
        raise RuntimeError(e)

    def _wait_for_connection(self):
        was_connected = self.wlan.isconnected()

        if not self.config['use_display'] and not self.wlan.isconnected():
            print("waiting for connection...")

        while not self.wlan.isconnected():
            if self.config['use_display']:
                self.oled.show(_app_name, "waiting for connection", separator = False)
                time.sleep_ms(500)
                self.oled.show(_app_name, "waiting for connection", separator = True)
                time.sleep_ms(500)

        if not was_connected:
            self._reset_button_presses()

    def _reset_button_presses(self):
        self.button_playpause.reset_press()
        self.button_next.reset_press()

    def _check_button_presses(self):
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
                    self.oled.show(_app_name, "saving track", separator = False)
                    currently_playing = self._get_currently_playing(api_tokens)
                    if currently_playing is not None:
                        if 'item' in currently_playing and 'id' in currently_playing['item']:
                            self._save_track(api_tokens, currently_playing['item'].get('id'))
                else:
                    self.oled.show(_app_name, "pausing playback", separator = False)
                    self.device_id = self._get_current_device_id(api_tokens)
                    self._pause_playback(api_tokens)
            else:
                self.oled.show(_app_name, "resuming playback", separator = False)
                self._resume_playback(api_tokens, self.device_id)

        elif self.button_next.was_pressed():
            print("next button pressed")
            if playing:
                if self.button_next.was_longpressed():
                    if self.pause_after_current:
                        self.oled.disable_status_dot()
                        self.oled.show(_app_name, "not pausing after current", separator = False)
                        self.pause_after_current = False
                    else:
                        self.oled.enable_status_dot(self.config['api_request_dot_size'])
                        self.oled.show(_app_name, "pausing after current", separator = False)
                        self.pause_after_current = True
                else:
                    self.oled.show(_app_name, "requesting next", separator = False)
                    self._next_playback(api_tokens)
            else:
                self.oled.show(_app_name, "requesting next", separator = False)
                self._next_playback(api_tokens, self.device_id)

        self._reset_button_presses()

    def _validate_api_reply(self, api_call_name, api_reply, ok_status_list = [], warn_status_list = [], raise_status_list = [], warn_duration_ms = 5000):
        print("{} status received: {}".format(api_call_name, api_reply['status_code']))

        if api_reply['status_code'] in ok_status_list:
            return True

        if api_reply['status_code'] in warn_status_list:
            warning_text = "{} api {}: {}".format(api_call_name, api_reply['status_code'], api_reply['text'])
            print(warning_text)
            self.oled.show(_app_name, warning_text, separator = False)
            time.sleep_ms(warn_duration_ms)
            return False

        if len(raise_status_list) == 0 or api_reply['status_code'] in raise_status_list:
            self.oled.show(_app_name, "{} api error {}".format(api_call_name, api_reply['status_code']), separator = False)
            raise RuntimeError("{} api error {} - {}".format(api_call_name, api_reply['status_code'], api_reply['text']))

        self.oled.show(_app_name, "{} api unhandled error {}".format(api_call_name, api_reply['status_code']), separator = False)
        raise RuntimeError("{} api unhandled status_code {} - {}".format(api_call_name, api_reply['status_code'], api_reply['text']))

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

        warn_status_list = []
        if 'timestamp' in api_tokens:
            warn_status_list.append(0)

        if not self._validate_api_reply("refresh", r, ok_status_list = [200], warn_status_list = warn_status_list):
            return api_tokens

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

        if not self._validate_api_reply("c-playing", r, ok_status_list = [200, 202, 204], warn_status_list = [0, 401, 403, 429]):
            return {'warn_shown': 1}

        if r['status_code'] != 200:
            return None

        if 'is_playing' not in r['json'] or r['json']['is_playing'] is not True or 'item' not in r['json']:
            if 'is_playing' not in r['json']:
                print("missing content, status unknown: {}".format(r['json']))
            return None

        return r['json']

    def _get_current_device_id(self, api_tokens):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.get_current_device_id(api_tokens)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("player", r, ok_status_list = [200], warn_status_list = [202, 204, 401, 403, 429])

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

        self._validate_api_reply("pause", r, ok_status_list = [200, 202, 204], warn_status_list = [0, 401, 403, 429])

        print("playback paused")

    def _resume_playback(self, api_tokens, device_id = None):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.resume_playback(api_tokens, device_id = device_id)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("resume", r, ok_status_list = [200, 202, 204, 404], warn_status_list = [403])

        if r['status_code'] == 404:
            print("no active device found")
            self.oled.show(_app_name, "no active device found", separator = False)
            time.sleep(3)
        else:
            print("playback resuming")

    def _next_playback(self, api_tokens, device_id = None):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.next_playback(api_tokens, device_id = device_id)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("next", r, ok_status_list = [200, 202, 204, 404], warn_status_list = [0, 401, 403, 429])

        if r['status_code'] == 404:
            print("no active device found")
            self.oled.show(_app_name, "no active device found", separator = False)
            time.sleep(3)
        else:
            print("playback next")

    def _save_track(self, api_tokens, track_id):
        self.oled.show_corner_dot(self.config['api_request_dot_size'])
        r = spotify_api.save_track(api_tokens, track_id)
        self.oled.hide_corner_dot(self.config['api_request_dot_size'])

        self._validate_api_reply("save track", r, ok_status_list = [200, 202, 204], warn_status_list = [0, 401, 403, 429])

        print("track saved")

    def _initial_token_request(self):
        import spotify_auth
        import machine

        self.oled.show("Login", "http:// {}.local".format(self.config['wlan']['mdns']), separator = False)
        authorization_code = spotify_auth.get_authorization_code(self.config['spotify']['client_id'], self.redirect_uri, self.ip, self.config['wlan']['mdns'])

        if authorization_code == None:
            self.oled.show(_app_name, "get_auth_code() failed", separator = False)
            raise RuntimeError("get_auth_code() failed")

        self.oled.show(_app_name, "authorized", separator = False)
        print("authorization_code content: {}".format(authorization_code))

        self._get_api_tokens(authorization_code)

        self.oled.show(_app_name, "authorized, rebooting", separator = False)
        time.sleep(2)
        machine.reset()

    async def _show_play_progress_for_seconds(self, api_tokens, cp, seconds):
        if 'progress_ms' not in cp or 'duration_ms' not in cp['item']:
            if cp.get('currently_playing_type', '') == 'track':
                self.oled.show(cp['item'].get('artists', [{}])[0].get('name', 'Unknown Artist'), cp['item'].get('name', 'Unknown Track'))
            elif cp.get('currently_playing_type', '') == 'episode':
                self.oled.show(cp['item'].get('show', {}).get('name', 'Unknown Podcast'), cp['item'].get('name', 'Unknown Episode'))
            else:
                self.oled.show("Unknown content", "")
            await asyncio.sleep(seconds)
        else:
            show_progress = True
            progress_start = time.time()
            progress = None

            if 'progress_ms' in cp and 'duration_ms' in cp['item']:
                progress_ms = cp['progress_ms']
                progress = True

            while True:
                interval_begins = time.ticks_ms()

                if progress is not None:
                    # compared remaining playback time needs to be longer than the 1000 ms loop interval and some approximation
                    # of the time it takes for the Spotify API call to get executed from display to Spotify server and
                    # then from Spotify server to playback client, the API doesn't directly support "pause after current",
                    # pausing early rather than late appears to be the better option
                    if self.pause_after_current and cp['item']['duration_ms'] - progress_ms <= 2000:
                        self._pause_playback(api_tokens)
                        break
                    if progress_ms > cp['item']['duration_ms']:
                        break
                    progress = progress_ms / cp['item']['duration_ms'] * 100

                playing_artist = "Unknown content"
                playing_title = ""

                if cp.get('currently_playing_type', '') == 'track':
                    playing_artist = cp['item'].get('artists', [{}])[0].get('name', 'Unknown Artist')
                    playing_title = cp['item'].get('name', 'Unknown Track')
                elif cp.get('currently_playing_type', '') == 'episode':
                    playing_artist = cp['item'].get('show', {}).get('name', 'Unknown Podcast')
                    playing_title = cp['item'].get('name', 'Unknown Episode')

                if show_progress:
                    self.oled.show(playing_artist, playing_title, progress = progress, ticks = self.config['show_progress_ticks'])
                    if not self.config['use_display']:
                        show_progress = False

                if time.time() >= progress_start + seconds:
                    break

                if await self._wait_for_button_press_ms(1000):
                    break

                progress_ms += time.ticks_diff(time.ticks_ms(), interval_begins)

    async def _wait_for_button_press_ms(self, milliseconds):
        interval_begins = time.ticks_ms()
        button_pressed = self._check_button_presses()

        while not button_pressed and time.ticks_diff(time.ticks_ms(), interval_begins) < milliseconds:
            await asyncio.sleep_ms(50)
            button_pressed = self._check_button_presses()

        return button_pressed

    async def _standby(self):
        print("standby")
        self._reset_button_presses()
        button_pressed = self._check_button_presses()

        if self.config['blank_oled_on_standby']:
            self.oled.clear()
        else:
            self.oled.standby()
            oled_updated = time.time()

        standby_start = time.time()

        while not button_pressed:
            if not self.config['blank_oled_on_standby']:
                if time.time() >= oled_updated + 10:
                    self.oled.standby()
                    oled_updated = time.time()
            button_pressed = await self._wait_for_button_press_ms(1000)
            if self.config['standby_status_poll_interval_minutes'] > 0:
                if time.time() >= standby_start + ( 60 * self.config['standby_status_poll_interval_minutes'] ):
                    print("standby status poll")
                    break

        if button_pressed:
            if not self.button_playpause.was_pressed():
                self._reset_button_presses()
            self.oled.show(_app_name, "resuming operations", separator = False)
            return True
        else:
            return False

    async def _start_standby(self, last_playing):
        loop_begins = time.time()
        show_progress = True

        while loop_begins + (self.config['status_poll_interval_seconds'] - 1) > time.time():

            standby_time = last_playing + self.config['idle_standby_minutes'] * 60
            progress = (standby_time - time.time()) / (self.config['idle_standby_minutes'] * 60) * 100

            if time.time() >= standby_time:
                return True

            if show_progress:
                self.oled.show("Spotify", "not playing", progress = progress, ticks = False)
                if not self.config['use_display']:
                    show_progress = False

            if await self._wait_for_button_press_ms(1000):
                return False

        return False

    async def _looper(self):
        self.oled.show(_app_name, "start", separator = False)

        api_tokens = None

        try:
            refresh_token_file = open('refresh_token.txt', 'r')
        except OSError:
            refresh_token_file = None

        if refresh_token_file is None:
            self._initial_token_request()
        else:
            refresh_token = refresh_token_file.readline().strip()
            refresh_token_file.close()
            api_tokens = self._refresh_access_token({ 'refresh_token': refresh_token })

        self.oled.show(_app_name, "tokenized", separator = False)
        print("api_tokens content: {}".format(api_tokens))

        playing = False
        last_playing = time.time()
        self._reset_button_presses()

        while True:
            gc.collect()
            gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
            if self.memdebug:
                mem_info()

            self._wait_for_connection()

            if 'expires_in' not in api_tokens or 'access_token' not in api_tokens or time.time() >= api_tokens['timestamp'] + api_tokens['expires_in'] - 30:
                api_tokens = self._refresh_access_token(api_tokens)
                if 'expires_in' not in api_tokens or 'access_token' not in api_tokens:
                    time.sleep_ms(1000)
                    continue

            self._handle_buttons(api_tokens, playing)

            currently_playing = self._get_currently_playing(api_tokens)

            if currently_playing is not None:
                if 'warn_shown' in currently_playing:
                    continue
                playing = True
                last_playing = time.time()
                if self.device_id is None:
                    self.device_id = self._get_current_device_id(api_tokens)
            else:
                playing = False
                self.pause_after_current = False
                self.oled.disable_status_dot()

            if playing:
                await self._show_play_progress_for_seconds(api_tokens, currently_playing, self.config['status_poll_interval_seconds'])
            else:
                if await self._start_standby(last_playing):
                    if await self._standby():
                        last_playing = time.time()
                    continue

    def start(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self._looper())
        except KeyboardInterrupt:
            print("keyboard interrupt received, stopping")
            self.oled.clear()
        except RuntimeError:
            raise
        except Exception as e:
            self.oled.show(e.__class__.__name__, str(e))
            raise
