# MIT License
# Copyright (c) 2023 Teemu Toivola
# https://github.com/vergoh/micropython-spotify-status-display

import socket
import select

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
                    cl.send("<html><head><title>Login complete</title></head><body>Login complete, this page can now be closed</body></html>\r\n")
                else:
                    cl.send("<html><head><title>Login error</title></head><body>{}</body></html>\r\n".format(params))
                cl.close()
                callback_code = params.get('code')
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
