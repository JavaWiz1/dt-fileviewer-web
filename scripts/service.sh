#!/bin/sh
export BASEDIR=/hosting/dt-fileviewer-web

cd $BASEDIR

/home/pi/.local/bin/poetry run python dt-fileviewer/main.py