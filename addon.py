#!/usr/bin/python
# -*- coding: utf-8 -*-
# Module: addon
# Author: DigitalLachance
# Created on: 24.04.2016
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import xbmcaddon
import xbmcgui
import xbmcplugin
import urllib, urllib2
import json
import os

# Get the plugin url in plugin:// notation.
__url__ = sys.argv[0]
# Get the plugin handle as an integer number.
__handle__ = int(sys.argv[1])

#the header used to pretend you are a browser
user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36'

#the url you will request to.
addonID = 'plugin.video.curiositystream'
base_url = 'https://api.curiositystream.com/v1/'
login_url = base_url + 'login'
home_url = base_url + 'sections/3/mobile?cache=true&collections=true&media_limit=1'
videoPage_url = base_url + 'media/'
cat_url = base_url + 'categories'
collect_url = base_url + 'collections/'
token = ''

__addon__ = xbmcaddon.Addon()
data_path = xbmc.translatePath(__addon__.getAddonInfo('profile'))
tokenFile = os.path.join(__addon__.getAddonInfo('path'), 'resources', 'data', 'token.txt')

# Write debug entry to kodi.log
def debug(txt):
	if isinstance (txt,str):
		txt = txt.decode("utf-8")	#if it is str we assume it's "utf-8" encoded.
									#will fail if called with other encodings (latin, etc) BE ADVISED!
	# At this point we are sure txt is a unicode string.
	message = u'%s: %s' % (__handle__, txt)
	xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)
	# I reencode to utf-8 because in many xbmc versions log doesn't admit unicode. 
	
def getJSON(url, token):
	debug('getJSON() - url - ' + url)

	req = urllib2.Request(url)
	if isinstance(token, str):
		req.add_header('X-Auth-Token', token)
		debug('Token set to: ' + token)

	req.add_header('User-Agent', user_agent)
	req.add_header('Referer', 'https://app.curiositystream.com/')
	req.add_header('Origin', 'https://app.curiositystream.com')
	response = urllib2.urlopen(req)
	source = response.read()
	response.close()

	return(source)

def retrieveToken():
	#read token from disk
	if os.path.isfile(tokenFile):
		with open(tokenFile, 'r') as infile:
			return(infile.read())
	
	return()

def login():
	my_addon = xbmcaddon.Addon()
	username = my_addon.getSetting('username')
	password = my_addon.getSetting('password')
	if username == '' or password == '':
		debug('No account information available to logon')
		return()
	
	#build the form data necessary for the login
	login_data = urllib.urlencode({'email':username, 'password':password})

	#build the request we will make
	req = urllib2.Request(login_url, login_data)
	req.add_header('User-Agent',user_agent)

	#do the login and get the response
	debug('Attempting to logon')
	try:
		response = urllib2.urlopen(req)
	except urllib2.HTTPError, e:	
		debug('HTTPError = ' + str(e.code))
		debug('Username used was: ' + username)
		debug('Password used was: ' + password)
		xbmcgui.Dialog().ok('Logon Error!', 'The username and/or password supplied is incorrect.', 'HTTP Error ' + str(e.code) + ' was returned') 
		return()

	response = urllib2.urlopen(req)
	source = response.read()
	response.close()
	debug('Logon finished!')

	# Response will be a JSON object
	response = json.loads(source)

	if response['status'] == 'success':
		token = response['message']['auth_token']
		debug('Wrote to file token: ' + token)
		with open(tokenFile, 'w') as outfile:
			outfile.write(token)
		return(token)

def list_categories(token):
	xbmcplugin.setContent(__handle__, 'episodes')
	
	# Fetch the home page content in order to build the Kodi menu.
	data = getJSON(home_url, token)
	debug('Home page retrieved')

	response = json.loads(data)
	groupings = response['data']['groups']

	# Create a list for our items.
	listing = []
	is_folder = True

	# Retrieve the category list
	data = getJSON(cat_url, token)
	temp = json.loads(data)
	categories = temp['data']
	cat = {}
	for category in categories:
		cat[category['name']] = category['image_url']

	# Loop through the groupings returned
	for group in groupings:
		list_item = xbmcgui.ListItem(label=group['label'])
		url = '{0}?action=listing&type={1}&name={2}&label={3}'.format(__url__, urllib.quote_plus(group['type']), urllib.quote_plus(group['name']), urllib.quote_plus(group['label']))
		debug('url = ' + url)
		if group['type'] == 'category':
			debug('Setting art to ' + cat[group['name']])
			list_item.setArt({'thumb': cat[group['name']], 'icon': cat[group['name']], 'fanart': cat[group['name']]})
		
		listing.append((url, list_item, is_folder))

	# Add our listing to Kodi.
	xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))

	# Add a sort method for the virtual folder items (alphabetically, ignore articles)
	xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)

	# Finish creating a virtual folder.
	xbmcplugin.endOfDirectory(__handle__)

def parameters_string_to_dict(parameters):
	paramDict = {}
	if parameters:
		paramPairs = parameters[1:].split("&")
		for paramsPair in paramPairs:
			paramSplits = paramsPair.split('=')
			if (len(paramSplits)) == 2:
				paramDict[paramSplits[0]] = paramSplits[1]
	return paramDict
	
def listCollection(collectionID, fanart):
	
	xbmcplugin.setContent(__handle__, 'episodes')
	token = retrieveToken()
	data = getJSON(collect_url + collectionID, token)
	temp = json.loads(data)
	collection = temp['data']
	listing = []
	debug('***** image_medium is ' + collection['image_medium'])
	for media in collection['media']:
		debug('##### Working on ' + media['title'])
		list_item = xbmcgui.ListItem(label=media['title'])
		list_item.setProperty('IsPlayable', 'true')
		list_item.setInfo('video', {'title': media['title'], 'genre': media['type'], 'year': media['year_produced'], 'rating': media['rating'], 'plot': media['description'], 'studio': media['producer'], 'duration': int(media['duration'])})
		list_item.setArt({'thumb': media['image_small'], 'icon':collection['image_medium'], 'fanart': fanart})

		url = '{0}?action=play&collection=false&id={1}'.format(__url__, media['id'])
		listing.append((url, list_item, False))
	
	xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
	xbmcplugin.endOfDirectory(__handle__)

def listVideos(type, name, label):
	
	xbmcplugin.setContent(__handle__, 'episodes')
	# Retrieve the token so we can make more authenticated calls to the web server.
	token = retrieveToken()

	page = 1
	url = 'https://api.curiositystream.com/v1/media?collections=true&filterBy={0}&limit=20&page={1}&term={2}'.format(type, page, name)
	debug('Opening page at ' + url)
	source = getJSON(url, token)
	
	debug('List of videos retrieved')
	videos = json.loads(source)
	listing = []
	totalPages = videos['paginator']['total_pages']
	debug('Total pages to retrieve = ' + str(totalPages))
	
	while page < totalPages or page < 5:
		for video in videos['data']:
			list_item = xbmcgui.ListItem(label=video['title'])
			# Set additional info for the list item.
			list_item.setInfo('video', {'title': video['title'], 'genre': video['type'], 'year': video['year_produced'], 'rating': video['rating'], 'plot': video['description'], 'studio': video['producer']})
			try:
				list_item.setInfo('video', {'duration': int(video['duration'])})
			except:
				debug('Could not set duration for ' + video['title'])
			else:
				debug('Moving on...')

			list_item.setArt({'thumb': video['image_small'], 'fanart': video['image_large']})
			if video['obj_type'] == 'collection':
				debug('Video ' + video['title'] + ' is a collection')
				list_item.setProperty('IsPlayable', 'false')
				url = '{0}?action=listCollection&id={1}&fanart={2}'.format(__url__, video['id'], urllib.quote_plus(video['image_medium']))
				is_folder = True
			else:
				is_folder = False
				list_item.setProperty('IsPlayable', 'true')
				list_item.setArt({'icon': video['image_medium']})
				url = '{0}?action=play&collection={1}&id={2}'.format(__url__, is_folder, video['id'])
				debug('Video ' + video['title'] + ' is NOT a collection')
			
			# Add our item to the listing as a 3-element tuple.
			listing.append((url, list_item, is_folder))

		page += 1
		url = 'https://api.curiositystream.com/v1/media?collections=true&filterBy={0}&limit=20&page={1}&term={2}'.format(type, page, name)
		debug('Opening page at ' + url)
		source = getJSON(url, token)
		videos = json.loads(source)
	
	xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
	# Add a sort method for the virtual folder items (alphabetically, ignore articles)
	xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
	xbmcplugin.endOfDirectory(__handle__)

def play(videoID):
	videoPage_url = base_url + 'media/' + videoID
	req = urllib2.Request(videoPage_url)
	
	#read token from disk
	token = retrieveToken()

	if isinstance(token, str):
		req.add_header('X-Auth-Token', token)
	req.add_header('User-Agent', user_agent)

	response = urllib2.urlopen(req)
	source = response.read()
	response.close()
	debug('Video page retrieved')

	response = json.loads(source)
	videoData = response['data']

	debug('****  Playing video ' + videoData['encodings'][0]['master_playlist_url'])
	listitem = xbmcgui.ListItem(path=videoData['encodings'][0]['master_playlist_url'])
	xbmcplugin.setResolvedUrl(__handle__, True, listitem)

params = parameters_string_to_dict(sys.argv[2])
action = urllib.unquote_plus(params.get('action', ''))
type = urllib.unquote_plus(params.get('type', ''))
name = urllib.unquote_plus(params.get('name', ''))
label = urllib.unquote_plus(params.get('label', ''))
videoID = urllib.unquote_plus(params.get('id', ''))
collection = urllib.unquote_plus(params.get('collection', ''))
fanart = urllib.unquote_plus(params.get('fanart', ''))

debug('tokenFile = ' + tokenFile)

if action == 'listing':
	listVideos(type, name, label)
elif action == 'play':
	play(videoID)
elif action == 'listCollection':
	listCollection(videoID, fanart)
else:
	if os.path.isfile(tokenFile):
		os.remove(tokenFile)
	token = login()
	if token != None:
		list_categories(token)
