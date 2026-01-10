###### OnClick Fetch Categories imoports #########
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_backend.settings')
import django
django.setup()
# import logging
import logging,os
from . import settings
# from celery.schedules import crontab
logger = logging.getLogger(__name__)
import requests
from django.http import JsonResponse
from inara.models import Item,Category,CategoryItem,TaskProgress,task_canceled,task_stopped
from unidecode import unidecode
import re
import random
# from celery.schedules import crontab
# from inara import views
# from inara.models import *
# Celery imports are done lazily to avoid import errors during Django startup
import datetime
# from celery.task.control import revoke

import environ
env = environ.Env()
environ.Env.read_env()
######## END ##############

logfmt = logging.Formatter("%(asctime)s %(levelname)s: %(name)s( %(module)s.%(funcName)s():%(lineno)d )- %(message)s")
celeryLogHandler = logging.handlers.TimedRotatingFileHandler(str(os.path.join(settings.LOGS_DIR, "celery.log")), when='midnight',backupCount=0, encoding=None, delay=False, utc=True)
celeryLogHandler.setFormatter(logfmt)
celeryLogger = logging.getLogger(__name__)
celeryLogger.setLevel(10)
celeryLogger.addHandler(celeryLogHandler)
celeryLogger.info('Logging enabled Tasks')

# Define task functions without decorators to avoid import errors
# They will be wrapped with task decorators when first accessed
# This allows Django to start even if Celery imports fail


def checkIfTaskCancelled(msg):
    # Import Ignore only when needed
    from celery.exceptions import Ignore
    if task_canceled():
        task_stopped()
        if(TaskProgress.objects.filter(syncType="ITEM_SYNC",status="PROGRESS").exists()):
            pass
        else:
            logger.info("Sync Item Process Stopped by user: Page No: %s " %(str(msg)))
            raise Ignore



def get_task_status(task_id):
    # Import AsyncResult and app here to avoid import errors during Django startup
    from celery.result import AsyncResult
    try:
        from .celery import app as celery_app
    except ImportError:
        try:
            from celery import current_app as celery_app
        except ImportError:
            celeryLogger.error('Cannot get Celery app for task status check')
            return {'status': 'UNKNOWN', 'progress': 0}
    
    task = AsyncResult(task_id, app=celery_app)
    status = task.status
    progress = 0 
    if status == 'SUCCESS':
        progress = 100
    elif status == 'FAILURE':
        progress = 0
    elif status == 'PROGRESS':
        progress = task.info.get('progress', 0)
    return {'status': status, 'progress': progress}


