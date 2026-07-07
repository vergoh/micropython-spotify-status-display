MDNS := spostatus
DEVICEHOST := $(MDNS).local

TARGETS = target/main.py target/buttonpress_async.mpy target/buzzer.mpy target/helpers.mpy target/oled.mpy target/spotify_api.mpy target/spotify_auth.mpy target/spotify.mpy target/ssd1306.mpy target/textutils.mpy target/uurequests.mpy target/cert.pem

default: mpy

.PHONY: check
check:
	pylint --disable=R,C,import-error,bare-except,too-many-locals,no-member,dangerous-default-value,broad-except,unspecified-encoding src

target:
	mkdir target

target/%.mpy: src/%.py | target
	mpy-cross $< -o $@

target/main.py: src/main.py | target
	cp -f src/main.py target/main.py

target/key.pem: | target
	openssl ecparam -name prime256v1 -genkey -noout -out $@
	chmod 600 $@

target/cert.pem: target/key.pem
	openssl req -new -x509 -sha256 -key $< -out $@ -days 3650 \
		-subj "/CN=$(DEVICEHOST)" \
		-addext "subjectAltName=DNS:$(DEVICEHOST)" \
		-addext "keyUsage=digitalSignature" \
		-addext "extendedKeyUsage=serverAuth" \
		-addext "basicConstraints=CA:FALSE"

.PHONY: mpy
mpy: $(TARGETS)

.PHONY: cert
cert: target/cert.pem

.PHONY: clean
clean:
	rm -fr target
