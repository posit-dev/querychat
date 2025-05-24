.PHONY: build publish create activate publish publish-test install-test

build:
	hatch build

publish:
	hatch publish

create:
	hatch env create

activate:
	hatch shell

publish:
	hatch publish

publish-test:
	hatch publish -r test

install-test:
	python3 -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/  querychat
