# Configuration

## Get Spotify client_id and client_secret

1. Login do [Spotify developer dashboard](https://developer.spotify.com/dashboard/login)
2. Select "Create an app"
3. Fill "Status display" or similar as app name, description can be a link to this project or anything else
4. Click "Edit setting" and add `https://spostatus.local/callback/` as "Redirect URI"
   - `spostatus` needs to match the `mdns` name configured in the next section
   - `https://` prefix and `.local/callback/` must remain as shown
   - Spotify requires HTTPS for non-loopback redirect URIs
5. Save the settings dialog
6. Click "Show client secret" and take note of both "Client ID" and "Client Secret"

## Edit src/config.json

1. Fill `client_id` and `client_secret` with values acquired in previous step
2. Fill `pins` section according to used wiring
3. Fill `wlan` section, use `mdns` value selected in previous step

## Generate TLS certificate

1. Run `make cert` (or `make` / `make mpy` to compile and generate certs in one step)
2. This creates ECDSA `prime256v1` `target/cert.pem` and `target/key.pem` for `https://spostatus.local` by default
   - ECDSA certificates use less ESP32 RAM during TLS handshakes than RSA
   - The Makefile `MDNS` variable should match `wlan.mdns` in `src/config.json` if you change the hostname
3. If `mdns` changes later, delete `target/cert.pem` and `target/key.pem`, update `MDNS` in the Makefile if needed, run `make cert`, and update the Spotify redirect URI

## Send implementation and config to device

1. Use MicroPython **1.23 or later** on the ESP32 (HTTPS login requires modern TLS cipher support; tested with 1.28)
2. Transfer the implementation using a serial connection with MicroPython command line
   - **Option 1** - direct source files, higher memory usage:
      1. With MicroPython command line, `put` the content of `src` directory to the root of the device
      2. Also `put` `target/cert.pem` and `target/key.pem` to the root of the device
   - **Option 2** - precompiled binaries, lower memory usage but requires extra step:
      1. With `mpy-cross` installed using `pip`, run `make` to compile the binaries and generate TLS certificates
         - The used `mpy-cross` version needs to match used MicroPython release, see [MicroPython documentation](https://docs.micropython.org/en/latest/reference/mpyfiles.html#versioning-and-compatibility-of-mpy-files) for version compatibility details
      2. With MicroPython command line, `put` the content of `target` directory to the root of the device
         - Possible previously installed `.py` files need to be removed before this step when upgrading
2. Start `repl` and soft reset the device with ctrl-d
3. Fix any possible configuration errors based on shown output
4. Login to Spotify using the device login page:
   1. Open `https://<mdns>.local` in a browser on the same network, for example `https://spostatus.local`
   2. Accept the browser warning for the self-signed certificate
   3. Complete Spotify login and approve the requested permissions
   4. Spotify redirects back to the device automatically

Spotify refresh tokens expire after 6 months from the initial authorization. When this happens, the display shows `login expired`, discards the old token, and starts the login flow again automatically at `https://<mdns>.local`. The device also stores `authorized_at.txt` with the authorization timestamp so expiry warnings can be added later if needed.

If a Spotify device doesn't currently have playback active then the display should reflect the situation. Start playback and the display should react to the change within the configured poll interval.
