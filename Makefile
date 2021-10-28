# Makefile.
#
# This is intended for convenience.
# All commands should be usable even without make.

# --- Variables

PROJECT := vanadium

# --- Rules

help:
	@echo "Make targets:"
	@echo ""
	@echo "Project builds:"
	@echo ""
	@echo "  Notes:"
	@echo "  - These commands need an active virtualenv and use Poetry."
	@echo "    There are Pip equivalents but they are not make targets."
	@echo ""
	@echo "  install     - Install non-dev dependencies and main package"
	@echo "  develop     - Install all dependencies and main package"
	@echo "  depends     - Install all dependencies without the main package"
	@echo ""
	@echo "  build       - Build all distributable Python packages."
	@echo "  build-sdist - Build project as source tarball."
	@echo "  build-wheel - Build project as wheel."
	@echo ""
	@echo "  clean       - Remove all built Python packages."
	@echo "  clean-sdist - Remove built tarballs."
	@echo "  clean-wheel - Remove built wheels."
	@echo ""

# Project builds

install:
	poetry install --no-dev

develop:
	poetry install

depends:
	poetry install --no-root

build: build-sdist build-wheel

clean: clean-sdist clean-wheel

build-sdist:
	poetry build -f sdist

clean-sdist:
	rm -f dist/$(PROJECT)*.tar.gz
	rmdir --ignore-fail-on-non-empty dist

build-wheel:
	poetry build -f wheel

clean-wheel:
	rm -f dist/$(PROJECT)*.whl
	rmdir --ignore-fail-on-non-empty dist
