TARGETS = target/main.py target/buttonpress_async.mpy target/buzzer.mpy target/helpers.mpy target/oled.mpy target/spotify_api.mpy target/spotify_auth.mpy target/spotify.mpy target/ssd1306.mpy target/textutils.mpy target/uurequests.mpy

default: mpy

.PHONY: check
check:
	pylint --disable=R,C,import-error,bare-except,too-many-locals,no-member,dangerous-default-value,broad-except,unspecified-encoding src

target:
	mkdir target

target/%.mpy: src/%.py target
	mpy-cross $< -o $@

target/main.py: src/main.py target
	cp -f src/main.py target/main.py

.PHONY: mpy
mpy: $(TARGETS)

.PHONY: clean
clean:
	rm -fr target
