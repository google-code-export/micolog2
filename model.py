﻿# -*- coding: utf-8 -*-
###################################################
#this file is under GPL v3 license
#Originally taken from Micolog
#Modified by Rex to reduce data store operations
##################################################

import os,logging
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import Model as DBModel
from google.appengine.api import mail
from google.appengine.api import urlfetch
from google.appengine.api import datastore
from datetime import datetime,timedelta
import urllib, hashlib,urlparse
import zipfile,re,pickle,uuid
from cache import *

logging.info('module base reloaded')

rootpath=os.path.dirname(__file__)

class Theme:
	def __init__(self, name='default'):
		self.name = name
		self.mapping_cache = {}
		self.dir = '/themes/%s' % name
		self.viewdir=os.path.join(rootpath, 'view')
		self.server_dir = os.path.join(rootpath, 'themes',self.name)
		if os.path.exists(self.server_dir):
			self.isZip=False
		else:
			self.isZip=True
			self.server_dir =self.server_dir+".zip"
		#self.server_dir=os.path.join(self.server_dir,"templates")
		logging.debug('server_dir:%s'%self.server_dir)

	def __getattr__(self, name):
		if self.mapping_cache.has_key(name):
			return self.mapping_cache[name]
		else:
			path ="/".join((self.name,'templates', name + '.html'))
			logging.debug('path:%s'%path)
			self.mapping_cache[name]=path
			return path

class ThemeIterator:
	def __init__(self, theme_path='themes'):
		self.iterating = False
		self.theme_path = theme_path
		self.list = []

	def __iter__(self):
		return self

	def next(self):
		if not self.iterating:
			self.iterating = True
			self.list = os.listdir(self.theme_path)
			self.cursor = 0

		if self.cursor >= len(self.list):
			self.iterating = False
			raise StopIteration
		else:
			value = self.list[self.cursor]
			self.cursor += 1
			if value.endswith('.zip'):
				value=value[:-4]
			return value
			#return (str(value), unicode(value))

class LangIterator:
	def __init__(self,path='locale'):
		self.iterating = False
		self.path = path
		self.list = []
		for value in  os.listdir(self.path):
				if os.path.isdir(os.path.join(self.path,value)):
					if os.path.exists(os.path.join(self.path,value,'LC_MESSAGES')):
						try:
							lang=open(os.path.join(self.path,value,'language')).readline()
							self.list.append({'code':value,'lang':lang})
						except:
							self.list.append( {'code':value,'lang':value})

	def __iter__(self):
		return self

	def next(self):
		if not self.iterating:
			self.iterating = True
			self.cursor = 0

		if self.cursor >= len(self.list):
			self.iterating = False
			raise StopIteration
		else:
			value = self.list[self.cursor]
			self.cursor += 1
			return value

	def getlang(self,language):
		from django.utils.translation import  to_locale
		for item in self.list:
			if item['code']==language or item['code']==to_locale(language):
				return item
		return {'code':'en_US','lang':'English'}

class BaseModel(db.Model):
	def __init__(self, parent=None, key_name=None, _app=None, **kwds):
		self.__isdirty = False
		DBModel.__init__(self, parent=None, key_name=None, _app=None, **kwds)#why this?

	def __setattr__(self,attrname,value):
		"""
		DataStore api stores all prop values say "email" is stored in "_email" so
		we intercept the set attribute, see if it has changed, then check for an
		onchanged method for that property to call
		"""
		if (attrname.find('_') != 0):
			if hasattr(self,'_' + attrname):
				curval = getattr(self,'_' + attrname)
				if curval != value:
					self.__isdirty = True
					if hasattr(self,attrname + '_onchange'):
						getattr(self,attrname + '_onchange')(curval,value)

		DBModel.__setattr__(self,attrname,value)

class Blog(db.Model):
	owner = db.UserProperty()
	author=db.StringProperty(default='admin')
	rpcuser=db.StringProperty(default='admin')
	rpcpassword=db.StringProperty(default='')
	description = db.TextProperty()
	baseurl = db.StringProperty(multiline=False,default=None)
	urlpath = db.StringProperty(multiline=False)
	title = db.StringProperty(multiline=False,default='Micolog')
	subtitle = db.StringProperty(multiline=False,default='This is a micro blog.')
	entrycount = db.IntegerProperty(default=0)
	posts_per_page= db.IntegerProperty(default=10)
	feedurl = db.StringProperty(multiline=False,default='/feed')
	blogversion = db.StringProperty(multiline=False,default='0.30')
	theme_name = db.StringProperty(multiline=False,default='default')
	enable_memcache = db.BooleanProperty(default = True)
	link_format=db.StringProperty(multiline=False,default='%(year)s/%(month)s/%(day)s/%(postname)s.html')
	comment_notify_mail=db.BooleanProperty(default=True)
	#评论顺序
	comments_order=db.IntegerProperty(default=0)
	#每页评论数
	comments_per_page=db.IntegerProperty(default=20)
	#comment check type 0-No 1-算术 2-验证码 3-客户端计算
	comment_check_type=db.IntegerProperty(default=1)
	#0 default 1 identicon
	avatar_style=db.IntegerProperty(default=0)

	blognotice=db.TextProperty(default='')

	domain=db.StringProperty()
	show_excerpt=db.BooleanProperty(default=True)
	version='2.0.0' #Micolog2's version number start from 2
	timedelta=db.FloatProperty(default=8.0)# hours #seems to be time zone specific?
	language=db.StringProperty(default="en-us")

	sitemap_entries=db.IntegerProperty(default=30)
	sitemap_include_category=db.BooleanProperty(default=False)
	sitemap_include_tag=db.BooleanProperty(default=False)
	sitemap_ping=db.BooleanProperty(default=False)
	default_link_format=db.StringProperty(multiline=False,default='?p=%(post_id)s')
	default_theme=Theme("default")

	allow_pingback=db.BooleanProperty(default=False)
	allow_trackback=db.BooleanProperty(default=False)

	theme=None
	langs=None
	application=None

	def __init__(self,
			   parent=None,
			   key_name=None,
			   _app=None,
			   _from_entity=False,
			   **kwds):
		from micolog_plugin import Plugins
		self.plugins=Plugins(self)
		db.Model.__init__(self,parent,key_name,_app,_from_entity,**kwds)

	def tigger_filter(self,name,content,*arg1,**arg2):
		return self.plugins.tigger_filter(name,content,blog=self,*arg1,**arg2)

	def tigger_action(self,name,*arg1,**arg2):
		return self.plugins.tigger_action(name,blog=self,*arg1,**arg2)

	def tigger_urlmap(self,url,*arg1,**arg2):
		return self.plugins.tigger_urlmap(url,blog=self,*arg1,**arg2)

	def get_ziplist(self):
		return self.plugins.get_ziplist();

	def save(self):
		self.put()

	def initialsetup(self):
		self.title = 'Your Blog Title'
		self.subtitle = 'Your Blog Subtitle'

	def get_theme(self):
		self.theme= Theme(self.theme_name);
		return self.theme

	def get_langs(self):
		self.langs=LangIterator()
		return self.langs

	def cur_language(self):
		return self.get_langs().getlang(self.language)

	def rootpath(self):
		return rootpath

	@object_cache(key_prefix='hotposts',is_hotposts=True)
	def hotposts(self):
		return Entry.all().filter('entrytype =','post').filter("published =", True).order('-readtimes').fetch(8)

	@object_cache(key_prefix='recentposts',is_aggregation=True)
	def recentposts(self):
		return Entry.all().filter('entrytype =','post').filter("published =", True).order('-date').fetch(8)

	def postscount(self):
		query = Entry.all().filter('entrytype =','post').filter("published =", True).order('-date')
		return get_query_count(query,cache_key='blog.postscount')

class Category(db.Model):
	uid=db.IntegerProperty()
	name=db.StringProperty(multiline=False)
	slug=db.StringProperty(multiline=False)
	parent_cat=db.SelfReferenceProperty()
	
	@property
	def posts(self):
		return Entry.all().filter('entrytype =','post').filter("published =", True).filter('categorie_keys =',self)

	@property
	def count(self):
		@object_memcache(key_prefix='category.count', time=3600*24)
		def __count():
			return Entry.all().filter('entrytype =','post').filter("published =", True).filter('categorie_keys =',self).count()
		return __count(cache_key=self.slug)

	def update_cache(self):
		ObjCache.flush_multi(is_htmlpage=True)
		ObjCache.update_basic_info(update_categories=True)

	def put(self):
		db.Model.put(self)
		self.update_cache()
		g_blog.tigger_action("save_category",self)

	def delete(self):
		for entry in Entry.all().filter('categorie_keys =',self):
			entry.categorie_keys.remove(self.key())
			entry.put()
		for cat in Category.all().filter('parent_cat =',self):
			cat.delete()
		db.Model.delete(self)
		self.update_cache()
		g_blog.tigger_action("delete_category",self)

	def ID(self):
		try:
			id=self.key().id()
			if id:
				return id
		except:
			pass

		if self.uid :
			return self.uid
		else:
			#旧版本Category没有ID,为了与wordpress兼容
			from random import randint
			uid=randint(0,99999999)
			cate=Category.all().filter('uid =',uid).get()
			while cate:
				uid=randint(0,99999999)
				cate=Category.all().filter('uid =',uid).get()
			self.uid=uid
			print uid
			self.put()
			return uid

	@classmethod
	def get_from_id(cls,id):
		cate=Category.get_by_id(id)
		if cate:
			return cate
		else:
			cate=Category.all().filter('uid =',id).get()
			return cate

	#no need to cache this
	@property
	def children(self):
		key=self.key()
		return [c for c in Category.all().filter('parent_cat =',self)]

	#don't cache this, since the only use is in admin page
	@classmethod
	def allTops(cls):
			return [c for c in Category.all() if not c.parent_cat]

class Archive(db.Model):
	monthyear = db.StringProperty(multiline=False)
	year = db.StringProperty(multiline=False)
	month = db.StringProperty(multiline=False)
	entrycount = db.IntegerProperty(default=0)
	date = db.DateTimeProperty(auto_now_add=True)

class Tag(db.Model):
	tag = db.StringProperty(multiline=False)
	tagcount = db.IntegerProperty(default=0) #可以指示拥有此tag的文章有多少个

	def posts(self):
		return Entry.all('entrytype =','post').filter("published =", True).filter('tags =',self)

	@classmethod
	def add(cls,value):
		if value:
			tag= Tag.get_by_key_name(value)
			if not tag:
				tag=Tag(key_name=value)
				tag.tag=value

			tag.tagcount+=1
			tag.put()
			return tag
		else:
			return None

	@classmethod
	def remove(cls,value):
		if value:
			tag= Tag.get_by_key_name(value)
			if tag:
				if tag.tagcount>1:
					tag.tagcount-=1
					tag.put()
				else:
					tag.delete()

class Link(db.Model):
	href = db.StringProperty(multiline=False,default='')
	linktype = db.StringProperty(multiline=False,default='blogroll')
	linktext = db.StringProperty(multiline=False,default='')
	linkcomment = db.StringProperty(multiline=False,default='')
	createdate=db.DateTimeProperty(auto_now=True)

	@property
	def get_icon_url(self):
		"get ico url of the wetsite"
		ico_path = '/favicon.ico'
		ix = self.href.find('/',len('http://') )
		return (ix>0 and self.href[:ix] or self.href ) + ico_path

	def put(self):
		db.Model.put(self)
		g_blog.tigger_action("save_link",self)


	def delete(self):
		db.Model.delete(self)
		g_blog.tigger_action("delete_link",self)

class Entry(BaseModel):
	author = db.UserProperty()
	author_name = db.StringProperty()
	published = db.BooleanProperty(default=False)
	content = db.TextProperty(default='')
	readtimes = db.IntegerProperty(default=0)
	title = db.StringProperty(multiline=False,default='')
	date = db.DateTimeProperty(auto_now_add=True)
	mod_date = db.DateTimeProperty(auto_now_add=True)
	tags = db.StringListProperty()
	categorie_keys=db.ListProperty(db.Key)
	slug = db.StringProperty(multiline=False,default='')
	link= db.StringProperty(multiline=False,default='')
	monthyear = db.StringProperty(multiline=False)
	entrytype = db.StringProperty(multiline=False,default='post',choices=[
		'post','page'])
	entry_parent=db.IntegerProperty(default=0)#When level=0 show on main menu.
	menu_order=db.IntegerProperty(default=0)
	commentcount = db.IntegerProperty(default=0)
	trackbackcount = db.IntegerProperty(default=0)

	allow_comment = db.BooleanProperty(default=True) #allow comment
	#allow_pingback=db.BooleanProperty(default=False)
	allow_trackback=db.BooleanProperty(default=True)
	password=db.StringProperty()

	#compatible with wordpress
	is_wp=db.BooleanProperty(default=False)
	post_id= db.IntegerProperty()
	excerpt=db.StringProperty(multiline=True)

	#external page
	is_external_page=db.BooleanProperty(default=False)
	target=db.StringProperty(default="_self")
	external_page_address=db.StringProperty()

	#keep in top
	sticky=db.BooleanProperty(default=False)

	postname=''
	_relatepost=None

	@property
	def content_excerpt(self):
		return self.get_content_excerpt(_('..more').decode('utf8'))

	def get_author_user(self):
		if not self.author:
			self.author=g_blog.owner
		return User.all().filter('email =',self.author.email()).get()

	def get_content_excerpt(self,more='..more'):
		if g_blog.show_excerpt:
			if self.excerpt:
				return self.excerpt+' <a href="/%s">%s</a>'%(self.link,more)
			else:
				sc=self.content.split('<!--more-->')
				if len(sc)>1:
					return sc[0]+u' <a href="/%s">%s</a>'%(self.link,more)
				else:
					return sc[0]
		else:
			return self.content

	def slug_onchange(self,curval,newval):
		if not (curval==newval):
			self.setpostname(newval)

	def setpostname(self,newval):
			 #check and fix double slug
			if newval:
				slugcount=Entry.all()\
						  .filter('entrytype',self.entrytype)\
						  .filter('date <',self.date)\
						  .filter('slug =',newval)\
						  .filter('published',True)\
						  .count()
				if slugcount>0:
					self.postname=newval+str(slugcount)
				else:
					self.postname=newval
			else:
				self.postname=""

	@property
	def fullurl(self):
		return g_blog.baseurl+'/'+self.link;

	@property
	def categories(self):
		try:
			return db.get(self.categorie_keys)
		except:
			return []

	@property
	def post_status(self):
		return  self.published and 'publish' or 'draft'

	def settags(self,values):
		if not values:tags=[]
		if type(values)==type([]):
			tags=values
		else:
			tags=[tag.strip() for tag in values.split(',')]

		if not self.tags:
			removelist=[]
			addlist=tags
		else:
			#search different  tags
			removelist=[n for n in self.tags if n not in tags]
			addlist=[n for n in tags if n not in self.tags]
		for v in removelist:
			Tag.remove(v)
		for v in addlist:
			Tag.add(v)
		self.tags=tags

	def comments(self):
		if g_blog.comments_order:
			return Comment.all().filter('entry =',self).order('-date')
		else:
			return Comment.all().filter('entry =',self).order('date')

	def comments_l(self):
		@object_cache(key_prefix='entry.comments',comment_type='ALL',is_aggregation=True)
		def _comments():
			if g_blog.comments_order:
				return [comment for comment in Comment.all().filter('entry =',self).order('-date').fetch(limit=1000)]
			else:
				return [comment for comment in Comment.all().filter('entry =',self).order('date').fetch(limit=1000)]
		return _comments(cache_entry_id=self.post_id, cache_key=str(self.post_id))

	def get_comments_by_page(self,index,psize):
		@object_cache(key_prefix='entry.get_comments_by_page', comment_type='ALL', is_pager=True)
		def _get_comments_by_page(index,psize):
			all_comments = self.comments_l()
			return all_comments[(index-1)*psize:index*psize]

		return _get_comments_by_page(index,psize,
		                                  cache_key=str(self.post_id)+'_'+str(index)+'_'+str(psize),
		                                  cache_entry_id = self.post_id
		                                  )

	@property
	def strtags(self):
		return ','.join(self.tags)

	@property
	def edit_url(self):
		return '/admin/%s?key=%s&action=edit'%(self.entrytype,self.key())

	def purecomments(self):
		@object_cache(key_prefix='entry.purecomments',comment_type='NORMAL', is_aggregation=True)
		def _purecomments():
			if g_blog.comments_order:
				return [comment for comment in Comment.all().filter('entry =',self).filter('ctype =',0).order('-date').fetch(limit=1000)]
			else:
				return [comment for comment in Comment.all().filter('entry =',self).filter('ctype =',0).order('date').fetch(limit=1000)]
		return _purecomments(cache_entry_id=self.post_id, cache_key=str(self.post_id))

	def purecomments_count(self):
		return get_query_count(
			query = self.purecomments(),
			cache_key = 'purecomments_count_'+str(self.post_id),
			cache_entry_id=self.post_id,
			cache_comment_type='NORMAL')

	def trackcomments(self):
		if g_blog.comments_order:
			return Comment.all().filter('entry =',self).filter('ctype IN',[1,2]).order('-date')
		else:
			return Comment.all().filter('entry =',self).filter('ctype IN',[1,2]).order('date')

	#seems nowhere uses
	#def commentsTops(self):
	#	return [c for c  in self.purecomments() if c.parent_key()==None]

	def delete_comments(self):
		cmts = Comment.all().filter('entry =',self)
		for comment in cmts:
			comment.delete()
		self.commentcount = 0
		self.trackbackcount = 0

		ObjCache.flush_multi(comment_type='ALL',entry_id=self.post_id)
		ObjCache.flush_multi(comment_type='NORMAL',entry_id=self.post_id)
		ObjCache.update_basic_info(update_comments=True)
		ObjCache.flush_multi(is_htmlpage=True,entry_id=self.post_id)

	def update_commentno(self):
		cmts = Comment.all().filter('entry =',self).order('date')
		i=1
		for comment in cmts:
			comment.no=i
			i+=1
			comment.store()
		ObjCache.flush_multi(comment_type='ALL',entry_id=self.post_id)#it's better to flush the cached comments as well
		ObjCache.flush_multi(comment_type='NORMAL',entry_id=self.post_id)

	def update_archive(self,cnt=1):
		"""Checks to see if there is a month-year entry for the
		month of current blog, if not creates it and increments count"""
		my = self.date.strftime('%B %Y') # September-2008
		sy = self.date.strftime('%Y') #2008
		sm = self.date.strftime('%m') #09

		archive = Archive.all().filter('monthyear',my).get()
		if self.entrytype == 'post':
			if not archive:
				archive = Archive(monthyear=my,year=sy,month=sm,entrycount=1)
				self.monthyear = my
				archive.put()
			else:
				# ratchet up the count
				archive.entrycount += cnt
				archive.put()
			try:
				ObjCache.update_basic_info(update_archives=True)
			except Exception,e:
				logging.error(e.message)
		g_blog.entrycount+=cnt
		g_blog.put()

	def save(self,is_publish=False):
		"""
		Use this instead of self.put(), as we do some other work here
		@is_pub:Check if need publish id
		"""
		g_blog.tigger_action("pre_save_post",self,is_publish)
		my = self.date.strftime('%B %Y') # September 2008
		self.monthyear = my
		old_publish=self.published
		self.mod_date=datetime.now()

		if is_publish:
			if not self.is_wp:
				self.put()
				self.post_id=self.key().id()

			#fix for old version
			if not self.postname:
				self.setpostname(self.slug)

			vals={'year':self.date.year,'month':str(self.date.month).zfill(2),'day':self.date.day,
				'postname':self.postname,'post_id':self.post_id}

			if self.entrytype=='page':
				if self.slug:
					self.link=self.postname
				else:
					#use external page address as link
					if self.is_external_page:
					   self.link=self.external_page_address
					else:
					   self.link=g_blog.default_link_format%vals
			else:
				if g_blog.link_format and self.postname:
					self.link=g_blog.link_format.strip()%vals
				else:
					self.link=g_blog.default_link_format%vals

		self.published=is_publish
		self.put()

		if is_publish:
			if g_blog.sitemap_ping:
				Sitemap_NotifySearch()

		if old_publish and not is_publish:
			self.update_archive(-1)
		if not old_publish and is_publish:
			self.update_archive(1)

		self.removecache()

		self.put()

		if self.entrytype=='PAGE':
			ObjCache.flush_multi(is_htmlpage=True)
		else:
			ObjCache.flush_multi(is_htmlpage=True, entry_id=self.post_id)
			ObjCache.flush_multi(is_htmlpage=True, is_aggregation=True)
			ObjCache.update_basic_info(update_pages=True)
			ObjCache.flush_multi(is_hotposts=True)

		g_blog.tigger_action("save_post",self,is_publish)

	def removecache(self):
		memcache.delete('/')
		memcache.delete('/'+self.link)
		memcache.delete('/sitemap')
		memcache.delete('blog.postcount')
		g_blog.tigger_action("clean_post_cache",self)

	@property
	def next(self):
		return Entry.all().filter('entrytype =','post').filter("published =", True).order('date').filter('date >',self.date).fetch(1)

	@property
	def prev(self):
		return Entry.all().filter('entrytype =','post').filter("published =", True).order('-date').filter('date <',self.date).fetch(1)

	@property
	def relateposts(self):
		@object_memcache(key_prefix='entry.relateposts', time=0)#time=0 means cache as long as possible
		def _relateposts():
			if  self._relatepost:
				return self._relatepost
			else:
				if self.tags:
					rposts_ids = {} #key is post id, value is Entry Object
					rposts_counts = {} #key is post id, value is count
					for tag in self.tags:
						rps = Entry.gql("WHERE published=True and tags=:1 and post_id!=:2 order by post_id desc ", tag, self.post_id).fetch(10)
						for rp in rps:
							if not rp.post_id in rposts_ids:
								rposts_counts[rp.post_id] = 1
								rposts_ids[rp.post_id] = rp
							else:
								rposts_counts[rp.post_id] = rposts_counts[rp.post_id] + 1

					mrps = sorted(rposts_counts.keys(), lambda x,y: cmp(rposts_counts[y], rposts_counts[x]))[0:10]
					self._relatepost = [rposts_ids[x] for x in mrps]
				else:
					self._relatepost= []
				return self._relatepost
		return _relateposts(cache_key=str(self.post_id))

	@property
	def trackbackurl(self):
		if self.link.find("?")>-1:
			return g_blog.baseurl+"/"+self.link+"&code="+str(self.key())
		else:
			return g_blog.baseurl+"/"+self.link+"?code="+str(self.key())

	def getbylink(self):
		pass

	def delete(self):
		g_blog.tigger_action("pre_delete_post",self)
		if self.published:
			self.update_archive(-1)
		self.delete_comments()
		db.Model.delete(self)
		if self.entrytype=='PAGE':
			ObjCache.flush_multi(is_htmlpage=True)
		else:#TODO Check
			ObjCache.flush_multi(is_htmlpage=True, entry_id=self.post_id)
			ObjCache.flush_multi(is_htmlpage=True, is_aggregation=True)
			ObjCache.update_basic_info(update_pages=True)

		g_blog.tigger_action("delete_post",self)

class User(db.Model):
	user = db.UserProperty(required = False)
	dispname = db.StringProperty()
	email=db.StringProperty()
	website = db.LinkProperty()
	isadmin=db.BooleanProperty(default=False)
	isAuthor=db.BooleanProperty(default=True)
	#rpcpwd=db.StringProperty()

	def __unicode__(self):
		#if self.dispname:
			return self.dispname
		#else:
		#	return self.user.nickname()

	def __str__(self):
		return self.__unicode__().encode('utf-8')

COMMENT_NORMAL=0
COMMENT_TRACKBACK=1
COMMENT_PINGBACK=2
class Comment(db.Model):
	entry = db.ReferenceProperty(Entry)
	date = db.DateTimeProperty(auto_now_add=True)
	content = db.TextProperty(required=True)
	author=db.StringProperty()
	email=db.EmailProperty()
	weburl=db.URLProperty()
	status=db.IntegerProperty(default=0)
	reply_notify_mail=db.BooleanProperty(default=False)
	ip=db.StringProperty()
	ctype=db.IntegerProperty(default=COMMENT_NORMAL)
	no=db.IntegerProperty(default=0)
	comment_order=db.IntegerProperty(default=1)

	@property
	def mpindex(self):
		count=self.entry.commentcount
		no=self.no
		if g_blog.comments_order:
			no=count-no+1
		index=no / g_blog.comments_per_page
		if no % g_blog.comments_per_page or no==0:
			index+=1
		return index

	@property
	def shortcontent(self,len=20):
		scontent=self.content
		scontent=re.sub(r'<br\s*/>',' ',scontent)
		scontent=re.sub(r'<[^>]+>','',scontent)
		scontent=re.sub(r'(@[\S]+)-\d{2,7}',r'\1:',scontent)
		return scontent[:len].replace('<','&lt;').replace('>','&gt;')

	def gravatar_url(self):

		# Set your variables here
		if g_blog.avatar_style==0:
			default = g_blog.baseurl+'/static/images/homsar.jpeg'
		else:
			default='identicon'

		if not self.email:
			return default

		size = 50

		try:
			# construct the url
			imgurl = "http://www.gravatar.com/avatar/"
			imgurl +=hashlib.md5(self.email.lower()).hexdigest()+"?"+ urllib.urlencode({
				'd':default, 's':str(size),'r':'G'})

			return imgurl
		except:
			return default

	def save(self):
		self.put()
		self.entry.commentcount+=1
		self.comment_order=self.entry.commentcount
		if (self.ctype == COMMENT_TRACKBACK) or (self.ctype == COMMENT_PINGBACK):
			self.entry.trackbackcount+=1
		self.entry.put()

		#update cache
		comment_count = ObjCache.get(comment_type='ALL',is_count=True,entry_id=self.entry.post_id)
		if comment_count is not None:
			count = ObjCache.get_cache_value(comment_count.cache_key)
			comment_count.update(count+1)

		comments_obj = ObjCache.get(comment_type='ALL',is_aggregation=True,entry_id=self.entry.post_id)
		if comments_obj:
			comments_val = ObjCache.get_cache_value(comments_obj.cache_key)
			if g_blog.comments_order:#递减
				comments_val.insert(0,self)
			else:
				comments_val.append(self)
			comments_obj.update(comments_val)
		#update entry.purecomments()
		if self.ctype == COMMENT_NORMAL:
			comment_count=ObjCache.get(comment_type='NORMAL',is_count=True,entry_id=self.entry.post_id)
			if comment_count is not None:
				count = ObjCache.get_cache_value(comment_count.cache_key)
				comment_count.update(count+1)

			comments_obj = ObjCache.get(comment_type='NORMAL',is_aggregation=True,entry_id=self.entry.post_id)
			if comments_obj:
				comments_val = ObjCache.get_cache_value(comments_obj.cache_key)
				if g_blog.comments_order:#递减
					comments_val.insert(0,self)
				else:
					comments_val.append(self)
				comments_obj.update(comments_val)

		ObjCache.flush_multi(comment_type='ALL',is_pager=True, entry_id=self.entry.post_id)
		ObjCache.flush_multi(comment_type='NORMAL',is_pager=True, entry_id=self.entry.post_id)
		#no need to invalidate all pages, home page is enough for most people
		ObjCache.flush_multi(is_htmlpage=True,is_aggregation=True)
		ObjCache.flush_multi(is_htmlpage=True,entry_id=self.entry.post_id)
		ObjCache.update_basic_info(update_comments=True)
		
		return True

	def delit(self):
		self.entry.commentcount-=1
		if self.entry.commentcount<0:
			self.entry.commentcount = 0
		if (self.ctype == COMMENT_TRACKBACK) or (self.ctype == COMMENT_PINGBACK):
			self.entry.trackbackcount-=1
		if self.entry.trackbackcount<0:
			self.entry.trackbackcount = 0
		self.entry.put()
		self.delete()

		#update cache
		comment_count = ObjCache.get(comment_type='ALL',is_count=True,entry_id=self.entry.post_id)
		if comment_count is not None:
			count = ObjCache.get_cache_value(comment_count.cache_key)
			comment_count.update(count-1)

		comments_obj = ObjCache.get(comment_type='ALL',is_aggregation=True,entry_id=self.entry.post_id)
		if comments_obj:
			comments_val = ObjCache.get_cache_value(comments_obj.cache_key)
			comments_val.remove(self)
			comments_obj.update(comments_val)
		#update entry.purecomments()
		if self.ctype == COMMENT_NORMAL:
			comment_count = ObjCache.get(comment_type='NORMAL',is_count=True,entry_id=self.entry.post_id)
			if comment_count is not None:
				count = ObjCache.get_cache_value(comment_count.cache_key)
				comment_count.update(count-1)

			comments_obj = ObjCache.get(comment_type='NORMAL',is_aggregation=True,entry_id=self.entry.post_id)
			if comments_obj:
				comments_val = ObjCache.get_cache_value(comments_obj.cache_key)
				comments_val.remove(self)
				comments_obj.update(comments_val)

		ObjCache.flush_multi(comment_type='ALL',is_pager=True, entry_id=self.entry.post_id)
		ObjCache.flush_multi(comment_type='NORMAL',is_pager=True, entry_id=self.entry.post_id)
		#no need to invalidate all pages, home page is enough for most people
		ObjCache.flush_multi(is_htmlpage=True,is_aggregation=True)
		ObjCache.flush_multi(is_htmlpage=True,entry_id=self.entry.post_id)
		ObjCache.update_basic_info(update_comments=True)

	#seems no need to update cache in this function
	def put(self):
		g_blog.tigger_action("pre_comment",self)
		db.Model.put(self)
		g_blog.tigger_action("save_comment",self)

	#seems no need to update cache in this function
	def delete(self):
		db.Model.delete(self)
		ObjCache.flush_multi(comment_type='ALL', entry_id=self.entry.post_id)
		ObjCache.flush_multi(comment_type='NORMAL', entry_id=self.entry.post_id)
		g_blog.tigger_action("delete_comment",self)

	#seems nowhere uses
	@property
	def children(self):
		key=self.key()
		comments=Comment.all().ancestor(self)
		return [c for c in comments if c.parent_key()==key]

	def store(self, **kwargs):
		rpc = datastore.GetRpcFromKwargs(kwargs)
		self._populate_internal_entity()
		return datastore.Put(self._entity, rpc=rpc)

class Media(db.Model):
	name =db.StringProperty()
	mtype=db.StringProperty()
	bits=db.BlobProperty()
	date=db.DateTimeProperty(auto_now_add=True)
	download=db.IntegerProperty(default=0)

	@property
	def size(self):
		return len(self.bits)

class OptionSet(db.Model):
	name=db.StringProperty()
	value=db.TextProperty()

	@classmethod
	def getValue(cls,name,default=None):
		try:
			opt=OptionSet.get_by_key_name(name)
			return pickle.loads(str(opt.value))
		except:
			return default

	@classmethod
	def setValue(cls,name,value):
		opt=OptionSet.get_or_insert(name)
		opt.name=name
		opt.value=pickle.dumps(value)
		opt.put()

	@classmethod
	def remove(cls,name):
		opt= OptionSet.get_by_key_name(name)
		if opt:
			opt.delete()

NOTIFICATION_SITES = [
  ('http', 'www.google.com', 'webmasters/sitemaps/ping', {}, '', 'sitemap')
  ]

def Sitemap_NotifySearch():
	""" Send notification of the new Sitemap(s) to the search engines. """


	url=g_blog.baseurl+"/sitemap"

	# Cycle through notifications
	# To understand this, see the comment near the NOTIFICATION_SITES comment
	for ping in NOTIFICATION_SITES:
	  query_map			 = ping[3]
	  query_attr			= ping[5]
	  query_map[query_attr] = url
	  query = urllib.urlencode(query_map)
	  notify = urlparse.urlunsplit((ping[0], ping[1], ping[2], query, ping[4]))
	  # Send the notification
	  logging.info('Notifying search engines. %s'%ping[1])
	  logging.info('url: %s'%notify)
	  try:
		  result = urlfetch.fetch(notify)
		  if result.status_code == 200:
			  logging.info('Notify Result: %s' % result.content)
		  if result.status_code == 404:
			  logging.info('HTTP error 404: Not Found')
			  logging.warning('Cannot contact: %s' % ping[1])

	  except :
		  logging.error('Cannot contact: %s' % ping[1])

def InitBlogData():
	global g_blog
	OptionSet.setValue('PluginActive',[u'googleAnalytics', u'wordpress', u'sys_plugin'])

	g_blog = Blog(key_name = 'default')
	g_blog.domain=os.environ['HTTP_HOST']
	g_blog.baseurl="http://"+g_blog.domain
	g_blog.feedurl=g_blog.baseurl+"/feed"
	os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
	lang="zh-cn"
	if os.environ.has_key('HTTP_ACCEPT_LANGUAGE'):
		lang=os.environ['HTTP_ACCEPT_LANGUAGE'].split(',')[0]
	from django.utils.translation import  activate,to_locale
	g_blog.language=to_locale(lang)
	from django.conf import settings
	settings._target = None
	activate(g_blog.language)
	g_blog.save()
	entry=Entry(title=u"欢迎使用Micolog2")
	entry.content=u'<p>Micolog2是对Micolog的数据库操作优化后的版本。在现有GAE的免费配额下，让您的博客重新轻松应对成百上千的日访问量。</p>'
	entry.content+=u'<p>Micolog2对主题部分的接口没有任何改动，因此您可以搭配已有的任何Micolog主题。</p>'
	entry.content+=u'<p>-- Rex</p>'
	entry.content+=u'<p>有关Micolog2的最新消息： http://micolog2.rexzhao.com</p>'
	
	entry.save(True)
	link=Link(href='http://blog.rexzhao.com',linktext="Rex's blog")
	link.put()
	link=Link(href='http://xuming.net',linktext="Xuming's blog")
	link.put()
	return g_blog

def gblog_init():
	global g_blog
	try:
	   if g_blog :
		   return g_blog
	except:
		pass
	g_blog = Blog.get_by_key_name('default')
	if not g_blog:
		g_blog=InitBlogData()

	g_blog.get_theme()
	g_blog.rootdir=os.path.dirname(__file__)
	return g_blog

try:
	g_blog=gblog_init()

	os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
	from django.utils.translation import activate
	from django.conf import settings
	settings._target = None
	activate(g_blog.language)
except Exception,e:
	logging.error(e.message)



