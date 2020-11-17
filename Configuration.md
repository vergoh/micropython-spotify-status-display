# Configuration

## Get Spotify client_id and client_secret

1. Login do [Spotify developer dashboard](https://developer.spotify.com/dashboard/login)
2. Select "Create an app"
3. Fill "Status display" or similar as app name, description can be a link to this project or anything else
4. Click "Edit setting" and add `http://spostatus.local/callback/` as "Redirect URI"
   - `spostatus` needs to match the `mdns` name configured in the next section
   - `http://` prefix and `.local/callback/` must remain as shown
5. Save the settings dialog
6. Click "Show client secret" and take note of both "Client ID" and "Client Secret"

## Edit src/config.json

1. Fill `client_id` and `client_secret` with values acquired in previous step
2. Fill `pins` section according to used wiring
3. Fill `wlan` section, use `mdns` value selected in previous step

## Send implementation and config to device

1. Using a serial connection to micropython command line, `put` the content of `src` directory to the root of the device
2. Start `repl` and soft reset the device with ctrl-d
3. Fix any possible configuration errors based on shown output
4. Login to Spotify using the provided url and accept requested permissions

If a Spotify device doesn't currently have playback active then the display should reflect the situation. Start playback and the display should react to the change within the configured poll interval.
