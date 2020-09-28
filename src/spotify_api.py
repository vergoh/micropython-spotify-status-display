# MIT License
# Copyright (c) 2020 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

import time
import ujson
import socket
import select

# imports from additional files
import uurequests as requests
from helpers import *

spotify_account_api_base = "https://accounts.spotify.com/api"
spotify_api_base = "https://api.spotify.com"

def _spotify_api_request(method, url, data = None, headers = None, retry = True):
    ret = {'status_code': 0, 'json': {}, 'text': ''}
    print("{} {}".format(method, url))
    r = requests.request(method, url, data = data, headers = headers)

    if r is None or r.status_code < 200 or r.status_code >= 500:
        if retry:
            if r is not None:
                r.close()
                del r
            time.sleep_ms(500)
            return _spotify_api_request(method, url, data = data, headers = headers, retry = False)
        else:
            return ret

    ret['status_code'] = r.status_code
    try:
        ret['json'] = r.json()
    except:
        ret['text'] = r.text

    r.close()
    del r
    return ret

def get_api_tokens(authorization_code, redirect_uri, client_id, client_secret):
    spotify_token_api_url = "{}/token".format(spotify_account_api_base)
    reqdata = { 'grant_type': 'authorization_code', 'code': authorization_code, 'redirect_uri': redirect_uri }

    b64_auth = "Basic {}".format(b64encode(b"{}:{}".format(client_id, client_secret)).decode())
    headers = { 'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': b64_auth }

    return _spotify_api_request("POST", spotify_token_api_url, data = urlencode(reqdata), headers = headers)

def refresh_access_token(api_tokens, client_id, client_secret):
    spotify_token_api_url = "{}/token".format(spotify_account_api_base)
    reqdata = { 'grant_type': 'refresh_token', 'refresh_token': api_tokens['refresh_token'] }

    b64_auth = "Basic {}".format(b64encode(b"{}:{}".format(client_id, client_secret)).decode())
    headers = { 'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': b64_auth }

    return _spotify_api_request("POST", spotify_token_api_url, data = urlencode(reqdata), headers = headers)

def get_currently_playing(api_tokens):
    spotify_player_api_url = "{}/v1/me/player/currently-playing".format(spotify_api_base)
    headers = { 'Authorization': "Bearer {}".format(api_tokens['access_token']) }

    return _spotify_api_request("GET", spotify_player_api_url, headers = headers)

def get_current_device_id(api_tokens):
    spotify_player_api_url = "{}/v1/me/player".format(spotify_api_base)
    headers = { 'Authorization': "Bearer {}".format(api_tokens['access_token']) }

    return _spotify_api_request("GET", spotify_player_api_url, headers = headers)

def pause_playback(api_tokens):
    spotify_player_api_url = "{}/v1/me/player/pause".format(spotify_api_base)
    headers = { 'Authorization': "Bearer {}".format(api_tokens['access_token']) }

    return _spotify_api_request("PUT", spotify_player_api_url, headers = headers)

def resume_playback(api_tokens, device_id = None):
    spotify_player_api_url = "{}/v1/me/player/play".format(spotify_api_base)
    headers = { 'Authorization': "Bearer {}".format(api_tokens['access_token']) }
    if device_id is not None:
        spotify_player_api_url += "?device_id={}".format(device_id)

    return _spotify_api_request("PUT", spotify_player_api_url, headers = headers)

def next_playback(api_tokens, device_id = None):
    spotify_player_api_url = "{}/v1/me/player/next".format(spotify_api_base)
    headers = { 'Authorization': "Bearer {}".format(api_tokens['access_token']) }
    if device_id is not None:
        spotify_player_api_url += "?device_id={}".format(device_id)

    return _spotify_api_request("POST", spotify_player_api_url, headers = headers)

def save_track(api_tokens, track_id):
    spotify_me_api_url = "{}/v1/me/tracks?ids={}".format(spotify_api_base, track_id)
    headers = { 'Authorization': "Bearer {}".format(api_tokens['access_token']) }

    return _spotify_api_request("PUT", spotify_me_api_url, headers = headers)

def get_authorization_code(client_id, redirect_uri, ip, mdns):
    spotify_auth_url = "https://accounts.spotify.com/authorize"
    scopes = "user-read-currently-playing user-read-playback-state user-modify-playback-state user-library-modify"

    user_login_url = "{}?client_id={}&response_type=code&redirect_uri={}&scope={}".format(spotify_auth_url, client_id, redirect_uri, scopes).replace(' ', '%20')

    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    http_server = socket.socket()
    http_server.bind(addr)
    http_server.listen(1)
    serv_counter = 0
    callback_code = None

    print("listening on {} as http://{} - login at http://{}.local".format(addr, ip, mdns))

    while True:
        read_sockets = [http_server]
        (r, _, _) = select.select(read_sockets, [], [])

        if http_server in r:
            reqpath = None
            cl, addr = http_server.accept()
            print("client connected from {}".format(addr))
            cl_file = cl.makefile('rwb', 0)
            while True:
                line = cl_file.readline()
                if not line or line == b'\r\n':
                    break
                else:
                    if line.startswith(b'GET '):
                        print(line.decode().strip())
                        reqpath = line.decode().strip().split(" ")[1]

            if reqpath is not None and reqpath.startswith('/callback') and '?' in reqpath:
                reqparams = reqpath.split('?')[1]
                params = {}
                for reqparam in reqparams.split('&'):
                    p = reqparam.split('=')
                    if len(p) != 2:
                        continue
                    params[p[0]] = p[1]
                print("got params: {}".format(params))
                cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                if 'code' in params:
                    cl.send("<html><head><title>Login complete</title></head><body>Login complete, this page can now be closed</body></html>\r\n".format(params))
                else:
                    cl.send("<html><head><title>Login error</title></head><body>{}</body></html>\r\n".format(params))
                cl.close()
                callback_code = params.get('code')
                if 'error' in params:
                    print("reply reports error: {}".format(params.get('error')))
                break
            elif reqpath is not None and reqpath == '/':
                print("not callback path, giving login")
                cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
                cl.send("<head><title>Redirect to login</title><meta http-equiv=\"Refresh\" content=\"0; URL={}\"></head>".format(user_login_url))
                cl.close()
            else:
                print("unknown path, sending 404")
                cl.send('HTTP/1.0 404 Not Found\r\nContent-type: text/plain\r\n\r\nNot Found\r\n')
                cl.close()

            serv_counter += 1
            if serv_counter == 5:
                print("counter limit reached")
                break

    http_server.close()

    return callback_code
