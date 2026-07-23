#!/usr/bin/env bash
set -e

echo "Installing OpenHub CLI..."

if command -v pipx >/dev/null 2>&1; then
    echo "Installing via pipx..."
    pipx install git+https://github.com/24KaratAu/openhub.git --force
elif command -v pip >/dev/null 2>&1; then
    echo "Installing via pip..."
    pip install --user git+https://github.com/24KaratAu/openhub.git
else
    echo "Error: Neither pip nor pipx found. Please install Python 3.10+ and pip."
    exit 1
fi

echo "OpenHub successfully installed."
echo "Run 'openhub' in your terminal to start."
