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

## Create and edit src/config.json

1. Create a copy of the file `src/config.json.bk` with the name of `src/config.json`
2. Fill `client_id` and `client_secret` with values acquired in previous step
3. Fill `pins` section according to used wiring
4. Fill `wlan` section, use `mdns` value selected in previous step

## Send implementation and config to device

1. Transfer the implementation using a serial connection with MicroPython command line
   - **Option 1** - direct source files, higher memory usage:
      1. With MicroPython command line, `put` the content of `src` directory to the root of the device
   - **Option 2** - precompiled binaries, lower memory usage but requires extra step:
      1. With `mpy-cross` installed using `pip`, run `make` to compile the binaries
         - The used `mpy-cross` version needs to match used MicroPython release, see [MicroPython documentation](https://docs.micropython.org/en/latest/reference/mpyfiles.html#versioning-and-compatibility-of-mpy-files) for version compatibility details
      2. With MicroPython command line, `put` the content of `target` directory to the root of the device
         - Possible previously installed `.py` files need to be removed before this step when upgrading
2. Start `repl` and soft reset the device with ctrl-d
3. Fix any possible configuration errors based on shown output
4. Login to Spotify using the provided url and accept requested permissions

If a Spotify device doesn't currently have playback active then the display should reflect the situation. Start playback and the display should react to the change within the configured poll interval.
