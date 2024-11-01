# dt-fileviewer-web
Python FastAPI web app used to view (text) files

Tested on Windows, RaspPI OS and Ubuntu.

# Purpose
Self-contained FastAPI web application you can place on your target host to expose text (specifically log) files to brower clients. 

This provides a quick way to view logs on target servers without ssh'ing to them to view the files.

Written in Python, using FastAPI (web container) and Bootstrap v5.2.3 (html/css framework).

# Requires
- Python 3.10+
- Poetry package manager

# Installation
On target server:
- Create hosting directory (i.e. /hosting) and cd into it.
- git clone https://github.com/JavaWiz1/dt-fileviewer-web.git
- cd into dt-fileviewer-web directory
- run: 
  - > poetry install
  - > poetry run python dt-fileviewer/main.py
- From a browser goto: http://<target server>/:8000

At this point a dialog should appear indicating that "Application configuration required."
In the form, add your files for viewing.  

- File ID is unique id string.
- Location must be a valid location on the target server.
