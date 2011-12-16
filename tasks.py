# -*- coding: utf-8 -*-
###################################################
#this file is under GPL v3 license
#Author: Rex  fdrex1987@gmail.com
##################################################
import logging
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from cache import ObjCache

class CleanCache(webapp.RequestHandler):
    def get(self):
        #is there any cache should we flush?
        logging.debug('TASK: Clean Cache finished')

application = webapp.WSGIApplication(
                                     [('/task/clean-cache', CleanCache)],
                                     debug=False)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
	main()