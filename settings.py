# -*- coding: utf-8 -*-
# Django settings for the example project.
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django','0.96')

DEBUG = True
TEMPLATE_DEBUG = False

##LANGUAGE_CODE = 'zh-CN'
##LANGUAGE_CODE = 'fr'
LOCALE_PATHS = 'locale'
USE_I18N = True

TEMPLATE_LOADERS=('django.template.loaders.filesystem.load_template_source',
                    'ziploader.zip_loader.load_template_source')