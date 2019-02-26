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

# the header used to pretend you are a browser
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'

# the url you will request to.
addonID = 'plugin.video.curiositystream'
base_url = 'https://api.curiositystream.com/v1/'
login_url = base_url + 'login'
home_url = base_url + 'sections/1/mobile?cache=true&collections=true&media_limit=1'
videoPage_url = base_url + 'media/'
cat_url = base_url + 'categories'
collect_url = base_url + 'collections/'
token = ''

__addon__ = xbmcaddon.Addon()
data_path = xbmc.translatePath(__addon__.getAddonInfo('profile'))
tokenFile = os.path.join(__addon__.getAddonInfo('path'), 'resources', 'data', 'token.txt')
media_path = os.path.join(__addon__.getAddonInfo('path'), 'resources', 'media')


# Write debug entry to kodi.log
def debug(txt):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")  # if it is str we assume it's "utf-8" encoded.
    # will fail if called with other encodings (latin, etc) BE ADVISED!
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
    req.add_header('Content-Type', 'application/json')
    req.add_header('Referer', 'https://app.curiositystream.com/')
    req.add_header('Origin', 'https://app.curiositystream.com')
    response = urllib2.urlopen(req)
    source = response.read()
    response.close()

    return (source)


def retrieveToken():
    # read token from disk
    if os.path.isfile(tokenFile):
        with open(tokenFile, 'r') as infile:
            return (infile.read())

    return ()


def login():
    my_addon = xbmcaddon.Addon()
    username = my_addon.getSetting('username')
    password = my_addon.getSetting('password')
    debug('username = ' + username)
    debug('password = ' + password)
    if username == '' or password == '':
        debug('No account information available to logon')
        return ()

    # logon information to be passed
    login_data = {'password':password,'email':username}

    # build the request we will make
    req = urllib2.Request(login_url, login_data)
    req.add_header('User-Agent', user_agent)
    req.add_header('content-type', 'application/json')

    # do the login and get the response
    debug('Attempting to logon')
    try:
        response = urllib2.urlopen(req, json.dumps(login_data))
    except urllib2.HTTPError, e:
        debug('HTTPError = ' + str(e.code))
        xbmcgui.Dialog().ok('Logon Error!', 'curiositystream.com returned the following message:',
        'The login credentials are incorrect. Please try again.')
        return ()

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
        return (token)


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
        cat[category['name']] = {'image': category['image_url'],
                                 'banner': category['header_url'],
                                 'background': category['background_url']}

    # Loop through the groupings returned
    for (ndx,group) in enumerate(groupings):
        list_item = xbmcgui.ListItem(label=group['label'])
        url = '{0}?action=listing&type={1}&name={2}&label={3}'.format(__url__, urllib.quote_plus(group['type']),
                                                                      urllib.quote_plus(group['name']),
                                                                      urllib.quote_plus(group['label']))
        debug('url = ' + url)
        if group['type'] == 'category':
            list_item.setInfo('video', {'title':group['label']})
            debug('Setting art to ' + cat[group['name']]['image'])
            list_item.setArt({'thumb': cat[group['name']]['image'], 
                              'icon': cat[group['name']]['image'], 
                              'poster': cat[group['name']]['image'],
                              'fanart': cat[group['name']]['image'],
                              'banner': cat[group['name']]['banner']})
        #elif group['type'] == 'custom':
        #    debug('Setting art to ' + cat[group['name']])
        else:
            list_item.setInfo('video', {'title':group['label'], 'sorttitle':'{} {}'.format(ndx+1,group['label'])})
            if len(group['media']) > 0:
                debug('Setting art to ' + group['media'][0]['image_small'])
                list_item.setArt({'thumb': group['media'][0]['image_small'], 
                                  'icon': group['media'][0]['image_small'], 
                                  'poster': group['media'][0]['image_small'],
                                  'fanart': group['media'][0]['image_small'],
                                  'banner': group['media'][0]['image_keyframe']})
        
        listing.append((url, list_item, is_folder))

    # Add the Watchlist as a group
    list_item = xbmcgui.ListItem(label='Watchlist')
    url = '{0}?action=listing&type={1}&name={2}&label={3}'.format(__url__,
                                                                  'bookmarked',
                                                                  'bookmarked',
                                                                  'Watchlist')
    #watchlist_image = 'https://art-u1.infcdn.net/articles_uploads/2014/02/TV-Apps.jpg'
    watchlist_image = os.path.join(media_path,'tv-apps.jpg')
    list_item.setArt({'thumb': watchlist_image,
                      'icon': watchlist_image,
                      'poster': watchlist_image,
                      'fanart': watchlist_image})
                      # Banner?
    list_item.setInfo('video', {'sorttitle':'0 Watchlist'})
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
        list_item.setInfo('video', {'title': media['title'], 'genre': media['type'], 'year': media['year_produced'],
                                    'rating': media['rating'], 'plot': media['description'],
                                    'studio': media['producer'], 'duration': int(media['duration'])})
        list_item.setArt({'thumb': media['image_small'], 'icon': collection['image_medium'], 'fanart': fanart})

        url = '{0}?action=play&collection=false&id={1}'.format(__url__, media['id'])
        listing.append((url, list_item, False))

    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.endOfDirectory(__handle__)


def listVideos(_type, name, label):
    xbmcplugin.setContent(__handle__, 'episodes')
    # Retrieve the token so we can make more authenticated calls to the web server.
    token = retrieveToken()

    page = 1
    url = 'https://api.curiositystream.com/v1/media?collections=true&filterBy={0}&limit=20&page={1}&term={2}'.format(
            _type, page, name)
    debug('Opening page at ' + url)
    source = getJSON(url, token)

    debug('List of videos retrieved')
    videos = json.loads(source)
    listing = []
    totalPages = videos['paginator']['total_pages']
    debug('Total pages to retrieve = ' + str(totalPages))

    while page < totalPages:
        for video in videos['data']:
            list_item = xbmcgui.ListItem(label=video['title'])
            # Set additional info for the list item.
            # Rating in Kodi is 0..10, here it is 0..5
            # Playcount of at least 1 means its been watched, but don't have an accurate watch count
            playcount = 0
            if  video.get('user_media') is not None:
                playcount = video.get('user_media').get('progress_percentage',0) > 75
            list_item.setInfo('video', {'title': video['title'], 
                                        'genre': video['type'], 
                                        'year': video['year_produced'],
                                        'rating': float(video['rating'])*2 if video['rating'] > 0 else None, 
                                        'plot': video['description'],
                                        'studio': video['producer'],
                                        'tagline': video.get('display_tag',''),
                                        'playcount':playcount})

            list_item.setArt({'thumb': video['image_small'], 'poster': video['image_large']})
            if video['obj_type'] == 'collection':
                debug('Video ' + video['title'] + ' is a collection')
                list_item.setProperty('IsPlayable', 'false')
                list_item.setArt({'fanart': video['image_large']})
                url = '{0}?action=listCollection&id={1}&fanart={2}'.format(__url__, video['id'],
                                                                           urllib.quote_plus(video['image_medium']))
                is_folder = True
            else:
                is_folder = False
                try:
                    list_item.setInfo('video', {'duration': int(video['duration'])})
                except:
                    debug('Could not set duration for ' + video['title'])
                else:
                    debug('Moving on...')

                list_item.setProperty('IsPlayable', 'true')
                list_item.setArt({'icon': video['image_medium'], 'fanart': video['image_keyframe']})
                url = '{0}?action=play&collection={1}&id={2}'.format(__url__, is_folder, video['id'])
                debug('Video ' + video['title'] + ' is NOT a collection')

            # Add our item to the listing as a 3-element tuple.
            listing.append((url, list_item, is_folder))

        page += 1
        url = 'https://api.curiositystream.com/v1/media?collections=true&filterBy={0}&limit=20&page={1}&term={2}'.format(
            _type, page, name)
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

    # read token from disk
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
_type = urllib.unquote_plus(params.get('type', ''))
name = urllib.unquote_plus(params.get('name', ''))
label = urllib.unquote_plus(params.get('label', ''))
videoID = urllib.unquote_plus(params.get('id', ''))
collection = urllib.unquote_plus(params.get('collection', ''))
fanart = urllib.unquote_plus(params.get('fanart', ''))

debug('tokenFile = ' + tokenFile)

if action == 'listing':
    listVideos(_type, name, label)
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
