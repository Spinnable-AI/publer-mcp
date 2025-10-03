.PHONY: install dev build lint

install:
	uv sync

dev:
	uv run python -m publer_mcp.server

build:
	uv build

lint:
	uv run ruff format publer_mcp
	uv run ruff check --fix --exclude ".scratch" --line-length 180 publer_mcp
