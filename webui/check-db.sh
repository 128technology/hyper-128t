#!/bin/sh

if ! [ -f app.db ]; then
	./populate_db.py
fi
