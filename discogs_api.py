import pandas as pd
import requests
import json
import time
import random
from datetime import date, datetime
import os


class discogs():

    @staticmethod 
    def pp_json(json_thing, sort=True, indents=4):
        if type(json_thing) is str:
            print(json.dumps(json.loads(json_thing), sort_keys=sort, indent=indents))
        else:
            print(json.dumps(json_thing, sort_keys=sort, indent=indents))
        #return None
    @staticmethod
    def json_serial(obj):

        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError ("Type %s not serializable" % type(obj))

    def __init__(self):
        self.url_ = "https://api.discogs.com/"
        self.t = 10
        self.key = os.getenv('DISCOGS_KEY')
        self.secret = os.getenv('DISCOGS_SECRET')
        self.headers = {"Authorization": f"Discogs key = {os.getenv('DISCOGS_KEY')}, secret = {os.getenv('DISCOGS_SECRET')}"}
        self.token = os.getenv('ADMIN_TOKEN')

    def get_release(self, release_id):
        url = f"{self.url_}releases/{release_id}"
        r = requests.get(url, headers = self.headers)
        self.rate_check(r.headers)
        r = requests.get(url, headers=self.headers)
        self.rate_check(r.headers)
        if r.status_code != 200:
            print("Failed request:", r.status_code, r.text)
            raise Exception(f"Discogs API Error {r.status_code}")
        #parsing_release_lists(r.json, release_id)
        return r.json()

    
    def master_release(self, master_id):
        '''
        master releases almost always have pagination built in so this needs to be handled here not in the loop
        '''
        
        url = f"{self.url_}masters/{master_id}/versions?per_page=100"
        r = requests.get(url, headers = self.headers)
        self.rate_check(r.headers)
        if r.status_code == 200:
            return(r.json())
        elif r.status_code == 429:
            print(r.text)
        else:
            time.sleep(10)
            print('sleeping')
            #is recurssion a smart way to do this? Maybe add a self.recursive depth to make sure you dont get stuck?
            return self.master_release(master_id)
    
    def artist(self, artist_id):
        url = f"{self.url_}artists/{artist_id}"
        r = requests.get(url, headers = self.headers)
        self.rate_check(r.headers)
        return(r.json())

    def artist_releases(self, artist_id):
        releases = []
        page = 1
        per_page = 100
        while True:
            url = f"{self.url_}artists/{artist_id}/releases"
            params = {
                "per_page": per_page,
                "page": page
            }
            r = requests.get(url, headers=self.headers, params=params)
            self.rate_check(r.headers)
            if r.status_code != 200:
                raise Exception(f"Discogs API Error {r.status_code}: {r.text}")
            data = r.json()
            releases.extend(data.get('releases', []))
            if page >= data['pagination']['pages']:
                break
            page += 1
        return releases
    
    def export_artist_releases_csv(self, artist_id):
        releases = self.artist_releases(artist_id)
        df = pd.DataFrame(releases)
        os.makedirs('output', exist_ok=True)
        
        path = f"output/artist_{artist_id}.csv"
        df.to_csv(path, index=False)
        return path

    def rate_check(self, r_head):
        used = int(r_head['X-Discogs-Ratelimit-Remaining'])
        #print(r_head['X-Discogs-Ratelimit-Remaining'])
        if used >=20:
            self.t = 10
        elif used <= 5:
            time.sleep(self.t)
            self.t += 5
            if self.t >= 60:
                self.t = 60

    def pagination(self, r):
        pass

    def parsing_release_lists(self,data):
        url = [] #will be 1 itme
        year = [] # will be 1 item
        labels = [] #could be multiple
        format_type = [] #list?
        format_qty = []
        catno = []
        tracks = []
        duration= []
        position = []
        notes = []
        for d in data['tracklist']:
            #print(d.keys())
            tracks.append(d['title'])
            duration.append(d['duration'])
            position.append(d['position'])
            try:
                url.append(data['uri'])
            except KeyError:
                url.append('not found')
            try:
                labels.append(data['labels'][0]['name'])
            except:
                labels.append('not found')
            try:
                catno.append(data['labels'][0]['catno'])
            except:
                catno.append('not found')
            try:
                format_type.append(data['formats'][0]['name'])
            except:
                format_type.append('not found')
            try:
                format_qty.append(data['formats'][0]['qty'])
            except:
                format_qty.append('not found')
            try:
                notes.append(data['notes'])
            except:
                notes.append('no notes')

        d = list(zip(url, labels,catno,format_type, format_qty, tracks, duration, position, notes))
        df = pd.DataFrame(d, columns = ['url', 'label', 'catno', 'format', 'format_qty', 'tracks', 'duration','position', 'notes'])
        os.makedirs("output", exist_ok=True)
        file = data['id']
        path = f'output/{file}.csv'
        df.to_csv(path, index=False)
        return path  # Return file path (NOT DataFrame)


'''
xx = discogs()
data = xx.get_release('5101485')
xx.parsing_release_lists(data)
'''
