.PHONY: help install test lint format clean run

PYTHON := python
UV := uv

help:
	@echo "Photo Meta Organizer"
	@echo ""
	@echo "Usage (Recommended):"
	@echo "  make run config=<path/to/params.json>"
	@echo "  Example: make run config=params/examples/organize.json"
	@echo ""
	@echo "Tasks available in JSON:"
	@echo "  organize   - Organize photos by date"
	@echo "  fix        - Fix metadata from folder names"
	@echo "  rename     - Batch rename files"
	@echo "  clean-junk - Move small files to junk"
	@echo ""
	@echo "Other Commands:"
	@echo "  make install             Install dependencies"
	@echo "  make test                Run tests"
	@echo "  make lint                Run linters"
	@echo ""

install:
	$(UV) sync

run:
	@if [ "$(config)" != "" ]; then \
		PYTHONPATH=src $(UV) run python -m photo_meta_organizer.cli run-task $(config) $(args); \
	else \
		PYTHONPATH=src $(UV) run python -m photo_meta_organizer.cli $(args); \
	fi

test:
	$(UV) run pytest tests/

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

clean:
	rm -rf dist build .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
