import urllib, urllib2, os, re, xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs, sys, string, MormonChannel2, tempfile, shutil, traceback
from base64 import b64decode
from BeautifulSoup import BeautifulSoup
try:
    import StorageServer
except:
    import storageserverdummy as StorageServer 
try:
    import json
except:
    import simplejson as json


HANDLE = int(sys.argv[1])
PATH = sys.argv[0]
QUALITY_TYPES = {'0':'360p','1':'720p','2':'1080p'}

def make_request(url, headers=None):
        if headers is None:
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:15.0) Gecko/20100101 Firefox/15.0.1'}
        try:
            req = urllib2.Request(url,None,headers)
            response = urllib2.urlopen(req)
            data = response.read()
            return data
        except urllib2.URLError, e:
            print 'We failed to open "%s".' % url
            if hasattr(e, 'reason'):
                print 'We failed to reach a server.'
                print 'Reason: ', e.reason
            if hasattr(e, 'code'):
                print 'We failed with error code - %s.' % e.code

def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                splitparams={}
                splitparams=pairsofparams[i].split('=')
                if (len(splitparams))==2:
                    param[splitparams[0]]=splitparams[1]
        return param



class Plugin():
    def __init__(self):
        self.cache = StorageServer.StorageServer("ldsvideos", 24)
        self.__settings__ = xbmcaddon.Addon(id='plugin.video.ldsvideos')
        self.__language__ = self.__settings__.getLocalizedString
        self.home = self.__settings__.getAddonInfo('path')
        self.icon = xbmc.translatePath( os.path.join( self.home, 'imgs', 'icon.png' ) )
        self.byufanart = xbmc.translatePath( os.path.join( self.home, 'imgs', 'byu-fanart.jpg' ) )
        self.byuicon = xbmc.translatePath( os.path.join( self.home, 'imgs', 'byu-icon.jpg' ) )
        self.mcicon = xbmc.translatePath( os.path.join( self.home, 'imgs', 'mc-icon.jpg' ) )
        self.mcfanart = xbmc.translatePath( os.path.join( self.home, 'imgs', 'mc-fanart.jpg' ) )
        self.fanart = xbmc.translatePath( os.path.join( self.home, 'imgs', 'gc-fanart.jpg' ) )
        self.ldsicon = self.icon
        self.dlpath = self.__settings__.getSetting('dlpath')
        # clear out latent items from the temp folder
        tempdir = xbmc.translatePath('special://temp')
        for filename in os.listdir(tempdir):
            if filename[:7] == "tmpimg-":
                try:
                    shutil.rmtree(os.path.join(tempdir,filename))
                except:
                    print "Couldn't delete folder %s from the temp folder" % os.path.join(tempdir,filename)

    def play_slideshow(self,url):
        res = urllib.urlopen(url)
        temp_folder = xbmc.translatePath('special://temp')
        dpath = tempfile.mkdtemp(prefix="tmpimg-",dir=temp_folder)
        temp_folder = os.path.join(temp_folder,dpath)
        extension = os.path.splitext(os.path.basename(url).split('?')[0])[1]
        if not extension: extension = "jpg"
        temp_file = os.path.join(temp_folder,"tmpimg." + extension)
        with open(temp_file,'wb') as f:
            f.write(res.read())
        res.close()
        
        xbmc.executebuiltin('SlideShow(%s)' % temp_folder)

    def resolve_url(self,url):
        print "Resolving URL: %s" % url
        item = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    def get_youtube_link(self,url):
        match=re.compile('https?://www.youtube.com/.+?v=(.+)').findall(url)
        link = 'plugin://plugin.video.youtube/?action=play_video&videoid='+ match[0]
        return link

    def add_link(self, thumb, info, urlparams, fanart=None, mtype="video"):
        if not fanart: fanart = self.fanart
        u=PATH+"?"+urllib.urlencode(urlparams)
        item=xbmcgui.ListItem(urlparams['name'], iconImage="DefaultVideo.png", thumbnailImage=thumb)
        item.setInfo(type=mtype, infoLabels=info)
        item.setProperty('IsPlayable', 'true')
        item.setProperty('Fanart_Image', fanart)
        try:
            if 'url' in urlparams:
                if urlparams['url'][-4:].upper() == '.MP4' or urlparams['url'][-4:].upper() == '.MP3' or urlparams['url'][-4:].upper() == '.JPG':
                    params = urllib.urlencode({'name':urlparams['name'],'url':urlparams['url'],'mode':"15"})
                    item.addContextMenuItems([('Download','XBMC.RunPlugin(%s?%s)' % (PATH,params))])
        except:
            pass
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=False)

    def add_dir(self,thumb,info, urlparams,fanart=None,mtype="video"):
        if not fanart: fanart = self.fanart
        u=PATH+"?"+urllib.urlencode(urlparams)
        item=xbmcgui.ListItem(urlparams['name'], iconImage="DefaultFolder.png", thumbnailImage=thumb)
        item.setInfo( type=mtype, infoLabels=info )
        item.setProperty('Fanart_Image', fanart)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=item,isFolder=True)

    def download(self,name,url):
        dialog = xbmcgui.Dialog()
        if not self.dlpath:
            dialog.ok("Download", "You must set the download folder location in the", "plugin settings before you can download anything")
            return
        if dialog.yesno("Download", 'Download "%s"?' % name):
            xbmc.executebuiltin('XBMC.Notification("Download","Beginning download...")')
            try:
                req = urllib2.urlopen(url)
                CHUNK = 16 * 1024
                with open(os.path.join(self.dlpath,os.path.basename(url)),'wb') as f:
                    for chunk in iter(lambda: req.read(CHUNK), ''):
                        f.write(chunk)
                xbmc.executebuiltin('XBMC.Notification("Download","Download complete")')
            except:
                print str(sys.exc_info())  
                xbmc.executebuiltin('XBMC.Notification("Download","Error downloading file")')
             
    def get_root_menu(self):
        self.add_dir(self.mcicon,{'Title':'Mormon Channel','Plot':'Watch and listen to content from the Mormon Channel'},{'name':'Mormon Channel','mode':14},self.mcfanart)
        self.add_dir(self.byuicon,{'Title':'BYU TV','Plot':'Watch videos from BYU TV'},{'name':'BYU TV','mode':1},self.byufanart)
        self.add_dir(self.ldsicon,{'Title':'LDS.org','Plot':'Watch videos from LDS.org'},{'name':'LDS.org','mode':1})

class LDSORG(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.icon = self.ldsicon
        self.postData = xbmc.translatePath(os.path.join(self.home, 'resources', 'req'))
        self.catUrl = 'http://www.lds.org/media-library/video/categories?lang=eng'
        self.headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:15.0) Gecko/20100101 Firefox/15.0.1',
                        'Referer' : 'http://www.lds.com'}
        self.gcLiveUrl = 'http://c.brightcove.com/services/mobile/streaming/index/rendition.m3u8'
        self.gcUrl = 'http://www.lds.org/general-conference/conferences?lang=eng'
        self.gcfanart = xbmc.translatePath( os.path.join( self.home, 'imgs', 'gc-fanart.jpg' ) )
        self.quality = QUALITY_TYPES[self.__settings__.getSetting('lds_quality')]

    def get_menu(self):
        #self.add_link(self.icon,{'Title':'General Conference Live','Plot':'Watch the General Conference live stream!'},
        #        {'name':'Conference Live','url':self.gcLiveUrl,'mode':3},self.gcfanart)
        self.add_dir(self.icon,{'Title':'LDS.org Featured Videos','Plot':'Watch LDS.org featured videos'},
                {'name':'Featured','url':'http://www.lds.org/media-library/video?lang=eng','mode':13},self.fanart)
        self.add_dir(self.icon,{'Title':'LDS.org Video Categories','Plot':'Watch LDS.org videos sorted by category'},
                {'name':'Categories','url':self.catUrl,'mode':2},self.fanart)
        self.add_dir(self.icon,{'Title':'LDS General Conference','Plot':'Watch all General Conferences provided on LDS.org'},
                {'name':'Conferences','mode':7},self.gcfanart)

    def get_categories(self,url):
        url = url + '&start=0&end=500&order=default'
        data = make_request(url)
        soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
        for i in soup.body.find("div",{"id":"primary"})("li"):
            name = i.h3.a.getText().encode('utf8')
            u = i.a['href']
            # we'll use the URL to determine if the link returns subcategories or video links
            if 'video/categories/' in i.a['href']:
                self.add_dir(i.img['src'],{'Title':name},{'name':name,'url':u,'mode':2},self.fanart)
            else:
                self.add_dir(i.img['src'],{'Title':name},{'name':name,'url':u,'mode':4},self.fanart)

    def get_video_list(self,url):
        if not url:
            return
        url = url + "&start=1&end=500&order=default"
        response = make_request(url)
        try:
            jsonData = response.split('video_data=')[1].split(';start_id=')[0]
        except:
            print "Didn't find any 'video_data'"
            return
        data = json.loads(jsonData)
        for k,v in data['videos'].iteritems():
            name = v['title'].encode('utf8')
            thumb = v['thumbURL']
            params = v['params']
            #duration = v['length']
            desc = v['description'].encode('utf8')
            for dl in v['downloads']:
                if dl['quality'] == self.quality:
                    href = dl['link']
                    size = dl['size']
                    break
            else:
                try:
                    href = v['downloads'][0]['link']
                except:
                    # If this fails then it indicates that the content can't be downloaded, we have to use a player for it
                    # Try to get the video from brightcove
                    href = self.get_brightcove_video(params)
                    if not href: continue
            self.add_link(thumb,{'Title':name,'Plot':desc},{'name':name,'url':href,'mode':5},self.fanart)

    # This function was taken from the General Conference plugin - https://github.com/viltsu/plugin.video.generalconference
    def resolve_brightcove_req_live(self,url):
        AMF_URL = 'http://c.brightcove.com/services/messagebroker/amf?playerKey=AQ~~,AAAAjP0hvGE~,N-ZbNsw4qBrgc4nqHfwj6D_S8kJzTvbq'
        LIVE_URL = url
        data = open(self.postData, 'rb')
        r = urllib2.Request(AMF_URL, data=data)
        r.add_header('Content-Type', 'application/x-amf')
        r.add_header('Content-Length', '150')
        u = urllib2.urlopen(r)
        content = u.read()
        u.close()
        content = filter(lambda x: x in string.printable, content)
        for m in re.finditer(LIVE_URL + "\?assetId=([0-9]*)", content):
            url = LIVE_URL + '?assetId=' + m.group(1)
            print "Resolving URL %s" % url
            item = xbmcgui.ListItem(path=url)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

    def get_brightcove_video(self,params):
        BC_URL = "https://secure.brightcove.com/services/viewer/htmlFederated"
        req = BC_URL + '?' + urllib.urlencode(params)
        print "Accessing Brightcove URL: %s" % req
        try:
            res = urllib2.urlopen(req).read()
            dic_str = res.split("var experienceJSON = ")[1].split(";\r\n")[0]
            js = json.loads(dic_str)
        except:
            print "ERROR: Couldn't parse Brightcove URL. %s" % traceback.format_exc().splitlines()[-1]
            return None
        largest = 0
        largest_url = None
        try:
            for r in js['data']['programmedContent']['videoPlayer']['mediaDTO']['renditions']:
                if int(r['frameHeight']) == self.quality:
                    return r['defaultURL']
                if int(r['frameHeight']) > largest:
                    largest = int(r['frameHeight'])
                    largest_url = r['defaultURL']
        except:
            print "ERROR: Couldn't handle Brightcove JSON. %s" % traceback.format_exc().splitlines()[-1]
        return largest_url

    def get_conferences(self,submode=None,url=None,sessionName=None):
        if not url:
            url = self.gcUrl
        thumb = self.icon
        data = make_request(url)
        soup = BeautifulSoup(data, convertEntities=BeautifulSoup.HTML_ENTITIES)
        if not submode: #Conference
	    # Spencer's Hack
	    scripts = soup("script")  #easier to parse from the javascript than the page now
	    script = scripts[3] #fourth script block in the page is the variable list
	    jsonValue = "{"+str(script).split('{', 1)[1].rsplit('}', 1)[0][0:-2]+"}"
	    value = json.loads(jsonValue)
	    for i in sorted(value, reverse=True):    
      		year = i.split()[1]
          	month = i.split()[0]
                u = "http://www.lds.org"+value[i]
                name = '%s %s' % (year,month)
                self.add_dir(thumb,{'Title':name,'Plot':'General Conference from %s of %s' % (month,year),'Year':year},
                            {'name':name,'url':u,'mode':7,'submode':2},self.gcfanart) #skip the session menu, go straight to talks
        elif submode == 1: #Session
            for i in soup.findAll("tr",{"class":"head-row"}):
                name = i.td.h2.getText()
                self.add_dir(thumb,{'Title':'%s Session' % name},{'name':name,'url':url,'mode':7,'submode':2},self.gcfanart)
            # Add the conference highlights
            try:
                u = soup.find(text=re.compile(r"General Conference Highlights")).parent.findNext('div').find("a",{"class":"video-%s" % self.quality,"type":"video/mp4"})['href']
                self.add_link(thumb,{'Title':'General Conference Highlights'},{'name':'Conference Highlights','url':u,'mode':5},self.gcfanart)
            except:
                pass
        elif submode == 2: #Talks
	    #f = open('debug.log', 'w')
            for i in soup.findAll("div",{"class":"lumen-tile lumen-tile--horizontal lumen-tile--list"}):
		title = i.findAll("div",{"class":"lumen-tile__title"})[0]("div")
		for bit in title:
			if not bit:
				continue;
			for b in bit:
				#f.write("BIT2:["+str(b)+"]")
				title = str(b)
			for j in i.findAll("img", {"class":"lumen-image__image"}):  #get the image placeholder because it has the same URL as the video
				# tweak it
				url = "http:"+j['src'].replace("/images/videos/", "/assets/").replace("media.ldscdn.org", "media2.ldscdn.org")
				url = url[0:-14]+"1080p-eng.mp4" 	
				#f.write(str(url))
				self.add_link(thumb,{'Title':title}, {'name':title,'url':url,'mode':5},self.gcfanart)
                #if i.td.h2.getText() == sessioniName:
                #    # Get the link for the entire session
                #    try:
                #        u = i.find("a",{"class":"video-%s" % self.quality,"type":"video/mp4"})['href']
                #        self.add_link(thumb,{'Title':sessionName + ' Session'},{'name':'All','url':u,'mode':5},self.gcfanart)
                #    except:
                #        pass
                    # Loop through all the nodes until we reach then next head-row then break
                #    node = i.findNext('tr')
                #    while (1):
                #        try:
                #            if not node or node['class'] == 'head-row': break
                #        except:
                #            pass
                        # Test if this is a talk by trying to get the talk class
                #        try: 
                #            talk = node.find('span',{'class':'talk'}).getText().encode('utf8')
                #        except: 
                #            node = node.findNext('tr')
                #            continue
                #        speaker = node.find('span',{'class':'speaker'}).getText().encode('utf8')
                #        try:
                #            u = node.find("a",{"class":"video-%s" % self.quality,"type":"video/mp4"})['href']
                #        except:
                #            try:
                #                u = node.find("a",{"type":"video/mp4"})['href']
                #            except:
                #                pass
                #        if u:
                #            title = "%s - %s" % (str(speaker),str(talk)) if talk and talk != "" else "%s" % str(speaker)
                #            self.add_link(thumb,{'Title':title},{'name':title,'url':u,'mode':5},self.gcfanart)
                #        speaker = None
                #        talk = None
                #        u = None
                #        node = node.findNext('tr')
                #    break
	    #f.close()

    def get_featured(self):
        url = 'http://www.lds.org/media-library/video?lang=eng'
        soup = BeautifulSoup(make_request(url), convertEntities=BeautifulSoup.HTML_ENTITIES)
        for i in soup.find('div',{'class':'feature-box'}).find('ul',{'class':"feature-preview"})('li'):
            fc = i.find('div',{'class':'feature-control'})
            name = fc.findNext('h3').getText().encode('utf8')
            desc = fc.p.getText().encode('utf8')
            u = fc.findNext('a')['href']
            thumb = "https://www.lds.org" + urllib.quote(i.findNext('img')['src'])
            if 'media-library/video/categories' in u: mode = 2
            else: mode = 4
            self.add_dir(thumb,{'Title':name,'Plot':desc},{'name':name,'url':u,'mode':mode},thumb)
        for i in soup.find('ul',{'class':'media-list'})('li'):
            name = i.findNext('h4').a.getText().encode('utf8')
            desc = i.findNext('p').getText().encode('utf8')
            u = i.find('a',{'class':'video-thumb-play'})['href']
            thumb = i.findNext('img')['src']
            try:
                soup2 = BeautifulSoup(make_request(u), convertEntities=BeautifulSoup.HTML_ENTITIES)
                for j in soup2.find('div',{'class':'galleryMeta'})('p'):
                    try:
                        if "for downloads" in j.a.getText():
                            u = j.a['href']
                            break
                    except:
                        continue
                else:
                    continue
            except:
                print "Couldn't get video link for %s. %s" % (name,traceback.format_exc().splitlines()[-1])
                continue
            if 'media-library/video/categories' in u: mode = 2
            else: mode = 4
            self.add_dir(thumb,{'Title':name,'Plot':desc},{'name':name,'url':u,'mode':mode},thumb)
            #self.get_video_list(u)

class BYUTV(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.icon = self.byuicon
        self.apiurl = 'http://www.byutv.org/api/Television/'
        self.fanart = self.byufanart
        #self.quality = QUALITY_TYPES[self.__settings__.getSetting('byu_quality')]

    def get_menu(self):
        self.add_link(self.icon,{'Title':'BYU TV','Plot':'BYU TV Live HD'},{'name':'BYU TV Live','mode':6},self.fanart)
        self.add_dir(self.icon,{'Title':'Categories','Plot':'Watch BYU TV videos by category'},{'name':'Categories','mode':8},self.fanart)
        self.add_dir(self.icon,{'Title':'All Shows','Plot':'Watch all BYU TV shows sorted alphabetically'},
                {'name':'Shows A-Z','mode':9,'submode':1},self.fanart)
        self.add_dir(self.icon,{'Title':'Popular Episodes','Plot':'Watch the most viewed BYU TV episodes'},
                {'name':'Popular Episodes','mode':12},self.fanart)

    def play_byu_live(self):
        soup = BeautifulSoup(make_request(self.apiurl + 'GetLiveStreamUrl?context=Android%24US%24Release'))
        urlCode = soup.getText().strip('"')
        reqUrl = 'http://player.ooyala.com/sas/player_api/v1/authorization/embed_code/Iyamk6YZTw8DxrC60h0fQipg3BfL/'+urlCode+'?device=android_3plus_sdk-hook&domain=www.ooyala.com&supportedFormats=mp4%2Cm3u8%2Cwv_hls%2Cwv_wvm2Cwv_mp4'
        data = json.loads(make_request(reqUrl))
        for stream in data['authorization_data'][urlCode]['streams']:
            url = b64decode(stream['url']['data'])
            item = xbmcgui.ListItem(path=url)
            try:
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)
            except:
                continue
    def get_categories(self):
        data = json.loads(make_request(self.apiurl + 'GetTVShowCategories?context=Android%24US%24Release'))
        for cat in data:
            self.add_dir(self.icon,{'Title':cat['name']},{'name':cat['name'],'mode':9})

    def get_shows(self,submode=None,cat=None):
        if not submode and cat:
            url = self.apiurl + 'GetShowsByCategory?context=Android%24US%24Release&categoryName=' + urllib.quote_plus(cat)
        if submode == 1:  #All shows
            url = self.apiurl + 'GetAllShows?context=Android%24US%24Release'
        data = json.loads(make_request(url))
        for show in data:
            desc = show['description']
            name = show['name']
            guid = show['guid']
            showCat = show['category']
            number = show['episodeCount']
            fanart = show['imageLarge']
            thumb = show['imageThumbnail']
            try: rating = show['rating']
            except: pass
            self.add_dir(thumb,{'Title':name,'Plot':desc,'Mpaa':rating},{'name':name,'mode':10,'guid':guid},fanart)

    def get_seasons(self,sguid):
        url = self.apiurl + "GetShowEpisodesByDate?context=Android%24US%24Release&showGuid=" + sguid
        data = json.loads(make_request(url))
        seasons = []
        fanart = []
        for episode in reversed(data):
            if episode['season'] not in seasons and episode['season']:
                seasons.append(episode['season'])
                fanart.append(episode['largeImage'])
        for index,season in enumerate(seasons):
            self.add_dir(self.icon,{'Title':season},{'name':season,'mode':11,'guid':sguid},fanart[index])
        if not seasons:
            self.get_episodes(None,sguid)

    def get_episodes(self,season,sguid,submode=None):
        if not submode: # By TV show
            url = self.apiurl + "GetShowEpisodesByDate?context=Android%24US%24Release&showGuid=" + sguid
        if submode == 1: # Weekly popular
            url = self.apiurl + "GetMostPopular?context=Android%24US%24Release&granularity=Week&numToReturn=500"
        if submode == 2: # Monly popular
            url = self.apiurl + "GetMostPopular?context=Android%24US%24Release&granularity=Month&numToReturn=500"
        if submode == 3: # Total popular
            url = self.apiurl + "GetMostPopular?context=Android%24US%24Release&granularity=Total&numToReturn=500"
        data = json.loads(make_request(url))
        index = 1
        for episode in reversed(data):
            if episode['season'] == season or submode or not episode['season']:
                desc = episode['description'].encode('utf8')
                name = episode['name'].encode('utf8')
                guid = episode['guid']
                ccurl = episode['captionFileUrl']
                fanart = episode['largeImage']
                date = episode['premiereDate']
                rating = episode['rating']
                duration = int(episode['runtime'])/60
                thumb = episode['thumbImage']
                u = episode['videoPlayUrl']
                show = episode['productionName'].encode('utf8')
                info = {'Title':name,'Plot':desc,'Premiered':date,'Season':season,
                        'TVShowTitle':show,'Mpaa':rating,'Year':date.split('-')[0]}
                if not submode:
                    name = '%02d - %s' % (index,name)
                else:
                    name = '%s - %s' % (show,name)
                self.add_link(thumb,info,{'name':name,'url':u,'mode':5},fanart)
                index = index + 1

    def get_popular(self):
        self.add_dir(self.icon,{'Title':'This Week','Plot':'Watch the most viewed episodes of this week'},
                {'name':'This Week','mode':11,'guid':'N/A','submode':1})
        self.add_dir(self.icon,{'Title':'This Month','Plot':'Watch the most viewed episodes of this month'},
                {'name':'This Month','mode':11,'guid':'N/A','submode':2})
        self.add_dir(self.icon,{'Title':'Ever','Plot':'Watch the most viewed episodes of all time'},
                {'name':'Ever','mode':11,'guid':'N/A','submode':3})


def main():
    xbmcplugin.setContent(HANDLE, 'tvshows')
    params=get_params()
    
    try:
        url=urllib.unquote_plus(params["url"])
    except:
        url=None
    try:
        name=urllib.unquote_plus(params["name"])
    except:
        name=None
    try:
        mode=int(params["mode"])
    except:
        mode=None
    try:
        submode=int(params["submode"])
    except:
        submode=None

    #print "Mode: "+str(mode)
    #print "URL: "+str(url)
    #print "Name: "+str(name)

    lds = LDSORG()
    byu = BYUTV()
    plugin = Plugin()
    mc = MormonChannel2.MormonChannel(plugin)

    if mode==None:
        plugin.get_root_menu()

    elif mode==1:
        if "LDS.org" in name:
            lds.get_menu()
        if "BYU TV" in name:
            byu.get_menu()

    elif mode==2:
        lds.get_categories(url)

    elif mode==3:
        lds.resolve_brightcove_req(url)

    elif mode==4:
        lds.get_video_list(url)

    elif mode==5:
        plugin.resolve_url(url)

    elif mode==6:
        byu.play_byu_live()

    elif mode==7:
        lds.get_conferences(submode,url,name)

    elif mode==8:
        byu.get_categories()

    elif mode==9:
        byu.get_shows(submode,name)

    elif mode==10:
        guid=urllib.unquote_plus(params["guid"])
        byu.get_seasons(guid)

    elif mode==11:
        guid=urllib.unquote_plus(params["guid"])
        byu.get_episodes(name,guid,submode)

    elif mode==12:
        byu.get_popular()

    elif mode==13:
        lds.get_featured()

    # Handle all MormonChannel modes
    elif mode==14:
        mc.broker(params)

    elif mode==15:
        plugin.download(name,url)

    elif mode==16:
        plugin.play_slideshow(url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


if __name__ == '__main__':
    main()

