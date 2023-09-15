SHELL := bash
.PHONY: vendor clean

vendor:
	python3 scripts/vendor.py

venv:
	python3 -m venv venv
	venv/bin/pip install -r requirements.txt

clean:
	git clean -xdf \
		-e tests/integration/cloud-config-hcloud.ini
