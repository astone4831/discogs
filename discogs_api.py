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

    
    def export_master_versions_csv(self, master_id):
        url = f"{self.url_}masters/{master_id}/versions?per_page=100"
        all_versions = []
        page = 1
        while True:
            r = requests.get(f"{url}&page={page}", headers=self.headers)
            self.rate_check(r.headers)
            if r.status_code != 200:
                raise Exception(f"Discogs API error {r.status_code}: {r.text}")
            data = r.json()
            versions = data.get('versions', [])
            all_versions.extend(versions)
            if page >= data['pagination']['pages']:
                break
            page += 1
        df = pd.DataFrame(all_versions)
        os.makedirs("output", exist_ok=True)
        path = f"output/master_{master_id}_versions.csv"
        df.to_csv(path, index=False)
        return path
    
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

    def parsing_release_lists(self, data, return_df=False):
    url = []
    year = []
    labels = []
    format_type = []
    format_qty = []
    catno = []
    tracks = []
    duration = []
    position = []
    notes = []
    title = []
    artist = []
    release_id = []
    for d in data.get('tracklist', []):
        tracks.append(d.get('title', ''))
        duration.append(d.get('duration', ''))
        position.append(d.get('position', ''))
        url.append(data.get('uri', 'not found'))
        title.append(data.get('title', 'not found'))
        artist.append(data.get('artists_sort', 'not found'))
        release_id.append(data.get('id'))
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
            notes.append(data.get('notes', 'no notes'))
        except:
            notes.append('no notes')
    d = list(zip(release_id, artist, title, url, labels, catno, format_type, format_qty, tracks, duration, position, notes))
    df = pd.DataFrame(d, columns=[
        'release_id', 'artist', 'release_title', 'url', 'label', 'catno',
        'format', 'format_qty', 'track_title', 'duration', 'position', 'notes'
    ])
    if return_df:
        return df
    # Original behavior for single release:
    file = data['id']
    df.to_csv(f'output/{file}.csv', index=False)
    return f'output/{file}.csv'
        
    def export_master_release_details_csv(self, master_id):
    print(f"Starting deep pull for master ID: {master_id}")
    url = f"{self.url_}masters/{master_id}/versions?per_page=100"
    all_ids = []
    page = 1
    while True:
        r = requests.get(f"{url}&page={page}", headers=self.headers)
        self.rate_check(r.headers)
        if r.status_code != 200:
            raise Exception(f"Discogs API error {r.status_code}: {r.text}")
        versions = r.json().get('versions', [])
        all_ids.extend([v['id'] for v in versions if 'id' in v])
        if page >= r.json()['pagination']['pages']:
            break
        page += 1
    print(f"Total release IDs to fetch: {len(all_ids)}")
    # This will collect all parsed DataFrames
    all_dfs = []
    for release_id in all_ids:
        try:
            time.sleep(0.3)
            release_data = self.get_release(release_id)
            # Reuse your tracklist flattener here
            df = self.parsing_release_lists(release_data, return_df=True)
            all_dfs.append(df)
        except Exception as e:
            print(f"Skipping release {release_id}: {e}")
            continue
    if not all_dfs:
        raise Exception("No releases could be processed.")
    final_df = pd.concat(all_dfs, ignore_index=True)
    os.makedirs("output", exist_ok=True)
    path = f"output/master_{master_id}_deep.csv"
    final_df.to_csv(path, index=False)
    print(f"Saved final deep CSV with {len(final_df)} rows to {path}")
    return path

'''
xx = discogs()
data = xx.get_release('5101485')
xx.parsing_release_lists(data)
'''
