.PHONY: start build pdf package

start:
	./start.sh

build:
	uv run python web/scripts/build_data.py
	npm --prefix web run build

pdf:
	uv run python web/scripts/build_data.py
	uv run python scripts/gerar_apresentacao.py

package: pdf
	uv run python scripts/empacotar_projeto.py
