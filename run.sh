#!/bin/bash
# Eurasian Bridge Dashboard Launcher
# Double-click this file or run: ./run.sh
set -e

cd "$(dirname "$0")"
streamlit run app.py
