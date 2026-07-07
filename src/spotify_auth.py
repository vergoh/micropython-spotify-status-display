# MIT License
# Copyright (c) 2023 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

import gc
import socket
import select
import ssl
from helpers import quote, urlencode

CERT_FILE = 'cert.pem'
KEY_FILE = 'key.pem'
HTTPS_PORT = 443

def _cert_files_present():
    for cert_file in (CERT_FILE, KEY_FILE):
        try:
            with open(cert_file, 'r') as f:
                if f.read(1) == '':
                    return False
        except OSError:
            return False
    return True

def _load_tls_credentials():
    try:
        with open(CERT_FILE, 'rb') as f:
            cert = f.read()
        with open(KEY_FILE, 'rb') as f:
            key = f.read()
    except OSError as e:
        print("failed to read TLS credentials: {}".format(e))
        return None, None

    if not cert or not key:
        print("TLS certificate files are empty: {} and {}".format(CERT_FILE, KEY_FILE))
        return None, None

    return cert, key

def _read_line(sock):
    line = b''
    while not line.endswith(b'\r\n'):
        chunk = sock.read(1)
        if not chunk:
            return None
        line += chunk
    return line

def _read_request_path(sock):
    line = _read_line(sock)
    if line is None:
        return None

    if line.startswith(b'GET '):
        print(line.decode().strip())
        parts = line.decode().strip().split(' ')
        if len(parts) >= 2:
            reqpath = parts[1]
        else:
            reqpath = None
    else:
        reqpath = None

    while True:
        line = _read_line(sock)
        if line is None or line == b'\r\n':
            break

    return reqpath

def _send_response(sock, status, content_type, body):
    if isinstance(body, str):
        body = body.encode()
    header = 'HTTP/1.0 {}\r\nContent-type: {}\r\n\r\n'.format(status, content_type)
    sock.write(header.encode())
    sock.write(body)

def get_authorization_code(client_id, redirect_uri, mdns):
    if not _cert_files_present():
        print("TLS certificate files missing: {} and {}".format(CERT_FILE, KEY_FILE))
        print("Run make cert and deploy both files to the device")
        return None

    cert, key = _load_tls_credentials()
    if cert is None:
        return None

    spotify_auth_url = "https://accounts.spotify.com/authorize"
    scopes = "user-read-currently-playing user-read-playback-state user-modify-playback-state user-library-modify"

    user_login_url = "{}?{}&scope={}".format(
        spotify_auth_url,
        urlencode({
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
        }),
        quote(scopes),
    )
    print("authorize scope param: {}".format(quote(scopes)))

    addr = socket.getaddrinfo('0.0.0.0', HTTPS_PORT)[0][-1]
    http_server = socket.socket()
    http_server.bind(addr)
    http_server.listen(1)
    serv_counter = 0
    callback_code = None

    print("listening for login at https://{}.local".format(mdns))

    while True:
        read_sockets = [http_server]
        (r, _, _) = select.select(read_sockets, [], [])

        if http_server in r:
            reqpath = None
            cl, client_addr = http_server.accept()
            print("client connected from {}".format(client_addr))
            gc.collect()
            try:
                cl = ssl.wrap_socket(cl, server_side=True, cert=cert, key=key)
            except (OSError, ValueError) as e:
                print("TLS handshake failed: {}".format(e))
                cl.close()
                gc.collect()
                continue

            reqpath = _read_request_path(cl)

            if reqpath is not None and reqpath.startswith('/callback') and '?' in reqpath:
                reqparams = reqpath.split('?')[1]
                params = {}
                for reqparam in reqparams.split('&'):
                    p = reqparam.split('=')
                    if len(p) != 2:
                        continue
                    params[p[0]] = p[1]
                print("got params: {}".format(params))
                if 'code' in params:
                    _send_response(cl, '200 OK', 'text/html', "<html><head><title>Login complete</title></head><body>Login complete, this page can now be closed</body></html>\r\n")
                    cl.close()
                    callback_code = params.get('code')
                    break
                elif 'error' in params:
                    oauth_error = params.get('error')
                    oauth_description = params.get('error_description', '')
                    print("oauth error: {} {}".format(oauth_error, oauth_description))
                    error_page = (
                        "<html><head><title>Login error</title></head><body>"
                        "<p>Spotify login failed: {}</p>"
                        "<p><a href=\"/\">Try again</a></p>"
                        "</body></html>\r\n"
                    ).format(oauth_error)
                    _send_response(cl, '200 OK', 'text/html', error_page)
                    cl.close()
                    continue
                else:
                    _send_response(cl, '200 OK', 'text/html', "<html><head><title>Login error</title></head><body>Missing authorization code. <a href=\"/\">Try again</a></body></html>\r\n")
                    cl.close()
                    continue
            elif reqpath is not None and reqpath == '/':
                print("not callback path, giving login")
                login_page = "<head><title>Redirect to login</title><meta http-equiv=\"Refresh\" content=\"0; URL={}\"></head>".format(user_login_url)
                _send_response(cl, '200 OK', 'text/html', login_page)
                cl.close()
            else:
                print("unknown path, sending 404")
                _send_response(cl, '404 Not Found', 'text/plain', "Not Found\r\n")
                cl.close()

            serv_counter += 1
            if serv_counter == 5:
                print("counter limit reached")
                break

    http_server.close()
    del cert, key
    gc.collect()

    return callback_code
