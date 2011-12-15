# -*- coding: utf-8 -*-
###################################################
#this file is under GPL v3 license
#Author: Rex  fdrex1987@gmail.com
#the code of format_date is from Micolog's code
##################################################
import logging
import pickle
from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime

class CacheUrlFormatter(object):
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

class ObjCache(db.Model):
	cache_key = db.StringProperty()
	value = db.BlobProperty()
	#the following fields are used at cache auto invalidation
	#一些Tag,用来标明该Obj的身份
	#因为查询的时候跟index域很相关，为了减少GAE统计的操作次数，这些标记全部放到StringList里面
	tags = db.StringListProperty()

#	is_htmlpage = db.BooleanProperty(default=False) #即request所缓存的那种
#	is_recentposts = db.BooleanProperty(default=False)
#	entry_type = db.StringProperty(default='') #'POST', 'PAGE
#	is_sticky = db.BooleanProperty(default=False)
#
#	is_comment = db.BooleanProperty(default=False)
#	comment_type = db.StringProperty(default='') #'ALL','NORMAL'
#
#	is_basicinfo = db.BooleanProperty(default=False)
#
#	is_relativePosts = db.BooleanProperty(default=False)
#
#	is_link = db.BooleanProperty(default=False)
#	is_tag = db.BooleanProperty(default=False)
#	is_category = db.BooleanProperty(default=False)
#	is_archive = db.BooleanProperty(default=False)
#
#	is_count = db.BooleanProperty(default=False)
#	is_aggregation = db.BooleanProperty(default=False)
#	is_pager = db.BooleanProperty(default=False)
#
#	category = db.StringProperty(default='')
#	entry_id = db.IntegerProperty(default=-1)#post_id
#	pager_id = db.IntegerProperty(default=-1)
#	tag = db.StringProperty(default='')
#	url = db.StringProperty(default='')

	def __init__(self,cache_key, value, is_htmlpage=False,is_recentposts=False,entry_type='',is_sticky=False,is_comment=False,
	             comment_type='',is_basicinfo=False,is_relativePosts=False,is_link=False,is_tag=False,is_category=False,
	             is_archive=False,is_count=False,is_aggregation=False,is_pager=False,category='',entry_id=-1,pager_id=-1,tag='',
	             url=''):
		l = []
		l.append('is_htmlpage='+str(is_htmlpage))
		l.append('is_recentposts='+str(is_recentposts))
		l.append('entry_type='+str(entry_type))
		l.append('is_sticky='+str(is_sticky))
		l.append('is_comment='+str(is_comment))
		l.append('comment_type='+str(comment_type))
		l.append('is_basicinfo='+str(is_basicinfo))
		l.append('is_relativePosts='+str(is_relativePosts))
		l.append('is_link='+str(is_link))
		l.append('is_tag='+str(is_tag))
		l.append('is_category='+str(is_category))
		l.append('is_archive='+str(is_archive))
		l.append('is_count='+str(is_count))
		l.append('is_aggregation='+str(is_aggregation))
		l.append('is_pager='+str(is_pager))
		l.append('category='+str(category))
		l.append('entry_id='+str(entry_id))
		l.append('pager_id='+str(pager_id))
		l.append('tag='+str(tag))
		l.append('url='+str(url))
		self.cache_key = cache_key
		self.value = value
		self.tags = l
		super(ObjCache,self).__init__()

	def invalidate(self):
		logging.debug('ObjCache invalidate called: ' + self.cache_key)
		memcache.delete(self.cache_key)
		self.delete()

	def update(self, new_value_obj):
		logging.debug('ObjCache update called: ' + self.cache_key)
		memcache.set(self.cache_key,new_value_obj)
		self.value = pickle.dumps(new_value_obj)
		self.put()

	@staticmethod
	def get_cache_value(key_name):
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
			return None

	@staticmethod
	def update_basic_info(
		update_categories=False,
		update_tags=False,
		update_links=False,
		update_comments=False,
		update_archives=False,
		update_pages=False):

		from model import Entry,Archive,Comment,Category,Tag,Link
		basic_info = ObjCache.all().filter('tags =','is_basicinfo=True').get()
		if basic_info is not None:
			info = ObjCache.get_cache_value(basic_info.cache_key)
			if update_pages:
				info['menu_pages'] = Entry.all().filter('entrytype =','page')\
							.filter('published =',True)\
							.filter('entry_parent =',0)\
							.order('menu_order').fetch(limit=1000)
			if update_archives:
				info['archives'] = Archive.all().order('-year').order('-month').fetch(12)
			if update_comments:
				info['recent_comments'] = Comment.all().order('-date').fetch(5)
			if update_links:
				info['blogroll'] = Link.all().filter('linktype =','blogroll').fetch(limit=1000)
			if update_tags:
				info['alltags'] = Tag.all().order('-tagcount').fetch(limit=100)
			if update_categories:
				info['categories'] = Category.all().fetch(limit=1000)
			basic_info.update(info)

	@staticmethod
	def create(key, value_obj, **kwargs):
		try:
			memcache.set(key,value_obj)
			ObjCache(cache_key=key,value=pickle.dumps(value_obj), **kwargs).put()
			logging.debug("ObjCache created: " + key)
		except Exception,e:
			logging.error(e.message)

	@staticmethod
	def flush_multi(**kwargs):
		flush = ObjCache.all()
		for key in kwargs:
			flush = flush.filter('tags =',key+'='+str(kwargs[key]))
		for obj in flush:
			obj.invalidate()

	@staticmethod
	def filter(**kwargs):
		result = ObjCache.all()
		for key in kwargs:
			result = result.filter('tags =',key+'='+str(kwargs[key]))
		return result

	@staticmethod
	def get(**kwargs):
		result = ObjCache.all()
		for key in kwargs:
			result = result.filter('tags =',key+'='+str(kwargs[key]))
		return result.get()

	@classmethod
	def flush_all(cls):
		'''
		This is faster than invalidate with default parameter values since memcache only need one call
		'''
		logging.debug('ObjCache flush all called')
		memcache.flush_all()
		for cache in ObjCache.all():
			cache.delete()

def object_cache(key_prefix='',
                 key_parameter_name='cache_key',
                 cache_parameter_prefix='cache_',
                 cache_control_parameter_name='cache_control',
                 **other_kwargs):
	'''
	available options for cache control are: no_cache, cache
	default option is cache
	'''
	def _decorate(method):
		def _wrapper(*args, **kwargs):
			key = 'obj_'+key_prefix
			if key_parameter_name in kwargs:
				key = key+'_'+kwargs[key_parameter_name]
				del kwargs[key_parameter_name]

			cache_control = 'cache'
			if cache_control_parameter_name in kwargs:
				cache_control = kwargs[cache_control_parameter_name]
				del kwargs[cache_control_parameter_name]
				
			cache_args = other_kwargs
			to_add = {}
			for parameter_name in kwargs:
				if parameter_name.startswith(cache_parameter_prefix):
					cache_arg_name = parameter_name[len(cache_parameter_prefix):]
					to_add[cache_arg_name] = kwargs[parameter_name]
					
			for parameter in to_add:
				cache_args[parameter] = to_add[parameter]
				del kwargs[cache_parameter_prefix + parameter]

			if cache_control == 'no_cache':
				logging.debug('object_cache: no_cache for '+key)
				return method(*args, **kwargs)

			result = ObjCache.get_cache_value(key)
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
			key = 'memcache_'+key_prefix
			if key_parameter_name in kwargs:
				key = key+'_'+kwargs[key_parameter_name]
				del kwargs[key_parameter_name]

			cache_control = 'cache'
			if cache_control_parameter_name in kwargs:
				cache_control = kwargs[cache_control_parameter_name]
				del kwargs[cache_control_parameter_name]

			if cache_control == 'no_cache':
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

@object_cache(key_prefix='get_query_count',is_count=True)
def get_query_count(query):
	if hasattr(query,'__len__'):
		return len(query)
	else:
		return query.count()

def format_date(dt):
	return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def request_cache(key_prefix='',
                  key_parameter_name='cache_key',
                  cache_parameter_prefix='cache_',
                  cache_control_parameter_name='cache_control',
                  **other_kwargs):
	'''
	available options for cache control are: no_cache, cache
	default option is cache
	'''
	def _decorate(method):
		def _wrapper(*args, **kwargs):
			request=args[0].request
			response=args[0].response

			key = 'request_'+key_prefix+'_'+request.path_qs
			if key_parameter_name in kwargs:
				key = key+'_'+kwargs[key_parameter_name]
				del kwargs[key_parameter_name]

			cache_control = 'cache'
			if cache_control_parameter_name in kwargs:
				cache_control = kwargs[cache_control_parameter_name]
				del kwargs[cache_control_parameter_name]
				
			cache_args = other_kwargs
			cache_args['is_htmlpage'] = True
			to_add = {}
			for parameter_name in kwargs:
				if parameter_name.startswith(cache_parameter_prefix):
					cache_arg_name = parameter_name[len(cache_parameter_prefix):]
					to_add[cache_arg_name] = kwargs[parameter_name]
			for parameter in to_add:
				cache_args[parameter] = to_add[parameter]
				del kwargs[cache_parameter_prefix + parameter]

			if cache_control == 'no_cache':
				logging.debug('request_cache: no_cache for '+key)
				if 'last-modified' not in response.headers:
						response.last_modified = format_date(datetime.utcnow())
				method(*args, **kwargs)
				return

			html= ObjCache.get_cache_value(key)
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
