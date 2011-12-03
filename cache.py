# -*- coding: utf-8 -*-
###################################################
#this file is under GPL v3 license
#Author: Rex  fdrex1987@gmail.com
#some of the code are come from Micolog's code
##################################################
import logging
import pickle
from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime


class ObjCache(db.Model):
	cache_key = db.StringProperty(multiline=False)
	value = db.BlobProperty()
	#the following fields are used at cache auto invalidation
	#divide the cases into the following basic categories:
	depend_post_id = db.IntegerProperty(default=-1) #which page's is this cache depends on
	depend_post_comments = db.IntegerProperty(default=-1) #which page's comments is this cache depends on (still use page id)
	depend_url = db.StringProperty(default='') #which url is this cache depends on
	depend_blog_roll = db.BooleanProperty(default=False) #is this cache depends on the blog roll

	def invalidate(self):
		logging.debug('ObjCache invalidate called: ' + self.cache_key)
		memcache.delete(self.cache_key)
		self.delete()

	def update(self, new_value_obj):
		logging.debug('ObjCache update called: ' + self.cache_key)
		memcache.set(self.cache_key,new_value_obj)
		self.value = pickle.dumps(new_value_obj)
		self.put()

	@classmethod
	def invalidate_multiple(cls, post_id=None,post_comments_id=None, url=None,blog_roll=None):
		query = ObjCache.all()
		if post_id is not None:
			query = query.filter('depend_post_id =',post_id)
		if post_comments_id is not None:
			query = query.filter('depend_post_comments =',post_comments_id)
		if url is not None:
			query = query.filter('depend_url =',url)
		if blog_roll is not None:
			query = query.filter('depend_blog_roll =',blog_roll)
		for obj in query:
			obj.invalidate()

	@classmethod
	def get(cls,key_name):
		result = memcache.get(key_name)
		if result is not None:
			return result
		try:
			result = ObjCache.all().filter('cache_key =',key_name).get()
			if result is not None:
				return pickle.loads(result.value)
			else:
				return None
		except Exception, e:
			logging.error(e.message)

	@classmethod
	def create(cls, key, value_obj, depend_post_id=-1,depend_post_comments=-1, depend_url='',depend_blog_roll=False):
		try:
			memcache.set(key,value_obj)
			ObjCache(cache_key=key,
					 value=pickle.dumps(value_obj),
					 depend_post_id=depend_post_id,
			         depend_post_comments = depend_post_comments,
					 depend_url=depend_url,
					 depend_blog_roll = depend_blog_roll
					 ).put()
			logging.debug("ObjCache created: " + key)
		except Exception,e:
			logging.error(e.message)

	@classmethod
	def flush_all(cls):
		'''
		This is faster than invalidate with default parameter values since memcache only need one call
		'''
		logging.debug('ObjCache flush all called')
		memcache.flush_all()
		for cache in ObjCache.all():
			cache.delete()

class CacheDependUrlGen(object):
	@staticmethod
	def gen_tag(slug):
		return '/tag/'+slug

	@staticmethod
	def gen_category(slug):
		return '/category/'+slug

	@staticmethod
	def gen_homepage():
		return '/'

	@staticmethod
	def gen_archive(year, month):
		return '/'+str(year)+'/'+str(month)

def object_cache(key_prefix='',
                 key_parameter_name='cache_key',
                 depend_post_id_parameter_name='cache_depend_post_id',
                 depend_post_comments_id_parameter_name='cache_depend_post_comments_id',
                 depend_url_parameter_name='cache_depend_url',
                 depend_blog_roll_parameter_name='cache_depend_blog_roll',
                 cache_control_parameter_name='cache_control'):
	'''
	available options for cache control are: no_cache, cache
	default option is cache
	'''
	def _decorate(method):
		def _wrapper(*args, **kwargs):
			key = key_prefix
			if key_parameter_name in kwargs:
				key = key+'_'+kwargs[key_parameter_name]
				del kwargs[key_parameter_name]

			cache_args = {}
			pd = {
				depend_post_id_parameter_name:'depend_post_id',
			    depend_post_comments_id_parameter_name:'depend_post_comments',
			    depend_url_parameter_name:'depend_url',
			    depend_blog_roll_parameter_name:'depend_blog_roll',
			}
			for parameter_name in pd:
				if parameter_name in kwargs:
					cache_args[pd[parameter_name]] = kwargs[parameter_name]
					del kwargs[parameter_name]
					
			cache_control = 'cache'
			if cache_control_parameter_name in kwargs:
				cache_control = kwargs[cache_control_parameter_name]
				del kwargs[cache_control_parameter_name]

			if cache_control == 'no cache':
				logging.debug('object_cache: no_cache for '+key)
				return method(*args, **kwargs)

			result = ObjCache.get(key)
			if result is not None:
				logging.debug('object_cache: result found for '+key)
				return result

			logging.debug('object_cache: result not found for '+key)
			result = method(*args, **kwargs)
			ObjCache.create(key,result,**cache_args)
			return result

		return _wrapper
	return _decorate

def object_memcache(key_prefix='',time=3600,
                 key_parameter_name='cache_key',
                 cache_control_parameter_name='cache_control'):
	'''
	available options for cache control are: no_cache, cache
	default option is cache
	'''
	def _decorate(method):
		def _wrapper(*args, **kwargs):
			key = key_prefix
			if key_parameter_name in kwargs:
				key = key+'_'+kwargs[key_parameter_name]
				del kwargs[key_parameter_name]

			cache_control = 'cache'
			if cache_control_parameter_name in kwargs:
				cache_control = kwargs[cache_control_parameter_name]
				del kwargs[cache_control_parameter_name]

			if cache_control == 'no cache':
				logging.debug('object_memcache: no_cache for '+key)
				return method(*args, **kwargs)

			result = memcache.get(key)
			if result is not None:
				logging.debug('object_memcache: found key for '+key)
				return result

			logging.debug('object_memcache: not found key for '+key)
			result = method(*args, **kwargs)
			memcache.set(key,result,time)
			return result
		return _wrapper
	return _decorate

@object_cache(key_prefix='get_query_count')
def get_query_count(query):
	return query.count()

def format_date(dt):
	return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def request_cache(key_prefix='',
                 depend_post_id_parameter_name='cache_depend_post_id',
                 depend_post_comments_id_parameter_name='cache_depend_post_comments_id',
                 depend_url_parameter_name='cache_depend_url',
                 depend_blog_roll_parameter_name='cache_depend_blog_roll',
                 cache_control_parameter_name='cache_control'):
	'''
	available options for cache control are: no_cache, cache
	default option is cache
	'''
	def _decorate(method):
		def _wrapper(*args, **kwargs):
			request=args[0].request
			response=args[0].response

			cache_args = {}
			pd = {
				depend_post_id_parameter_name:'depend_post_id',
			    depend_post_comments_id_parameter_name:'depend_post_comments',
			    depend_url_parameter_name:'depend_url',
			    depend_blog_roll_parameter_name:'depend_blog_roll',
			}
			for parameter_name in pd:
				if parameter_name in kwargs:
					cache_args[pd[parameter_name]] = kwargs[parameter_name]
					del kwargs[parameter_name]

			cache_control = 'cache'
			if cache_control_parameter_name in kwargs:
				cache_control = kwargs[cache_control_parameter_name]
				del kwargs[cache_control_parameter_name]

			key = key_prefix
			if key == '':
				key = request.path_qs
			else:
				key = key+'_'+request.path_qs

			if cache_control == 'no cache':
				logging.debug('request_cache: no_cache for '+key)
				if 'last-modified' not in response.headers:
						response.last_modified = format_date(datetime.utcnow())
				method(*args, **kwargs)
				return

			html= ObjCache.get(key)
			if html:
				logging.debug('request_cache: found cache for '+key)
				try:
					response.last_modified =html[1]
					_len=len(html)
					if _len>=3:
						response.set_status(html[2])
					if _len>=4:
						for h_key,value in html[3].items():
							response.headers[h_key]=value
					response.out.write(html[0])
					return
				except Exception,e:
					logging.error(e.message)

			logging.debug('request_cache: not found cache for '+key)

			if 'last-modified' not in response.headers:
				response.last_modified = format_date(datetime.utcnow())

			method(*args, **kwargs)
			result=response.out.getvalue()
			status_code = response._Response__status[0]
			html = (result,response.last_modified,status_code,response.headers)
			ObjCache.create(key,html,**cache_args)
			return

		return _wrapper
	return _decorate
