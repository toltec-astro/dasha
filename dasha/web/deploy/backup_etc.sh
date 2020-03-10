#!/bin/bash

for p in /etc/apache2/sites-enabled/500-gunicorn.conf \
	/etc/redis/redis.conf \
	/etc/systemd/system/gunicorn@.socket \
	/etc/systemd/system/gunicorn@.service \
	/etc/systemd/system/celery@.service \
	/etc/systemd/system/celerybeat@.service \
	/etc/systemd/system/celeryflower@.service; do
	echo copy ${p} to ./
	cp ${p} ./
done
