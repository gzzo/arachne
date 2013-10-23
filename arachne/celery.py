from __future__ import absolute_import

from celery import Celery

celery = Celery('arachne.celery')
celery.config_from_object('celeryconfig')