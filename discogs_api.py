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

    @staticmethod
    def format_to_mm_ss(time_string):
        try:
            if not time_string or ":" not in time_string:
                return None
            parts = list(map(int, time_string.split(":")))
            if len(parts) == 2:
                minutes, seconds = parts
            elif len(parts) == 3:
                hours, minutes, seconds = parts
                minutes += hours * 60
            else:
                return None
            return f"{minutes}:{seconds:02}"
        except:
            return None

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

    def get_all_label_release(self, label_id):
        releases = []
        page = 1
        per_page = 100
        while True:
            url = f"{self.url_}labels/{label_id}/releases"
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

    def search_artist_and_release(self, artist_name, release_title):
        # Build a single “q” param for full-text search
        full_query = f"{artist_name} {release_title}".strip()
        params = {
            "q": full_query,
            "type": "release",
            "per_page": 10,
            "key": self.key,
            "secret": self.secret
        }
        r = requests.get(f"{self.url_}database/search", params=params)
        r.raise_for_status()
        return r.json().get("results", [])

    def parsing_release_lists(self, data, return_df=False, selected_cols=None):
        rows = []
        for d in data.get('tracklist', []):#this needs to be position, title, duration also add country of origin
            rows.append({
                'release_id': data['id'],
                'track_title': d.get('title'),
                'duration': self.format_to_mm_ss(d.get('duration')),
                'position': f"'{d.get('position')}",
                'release_title': data.get('title'),
                'artist': data.get('artists_sort'),
                'label': data.get('labels', [{}])[0].get('name'),
                'format': data.get('formats', [{}])[0].get('name'),
                'catno': data.get('labels', [{}])[0].get('catno'),
                'release_url': data.get('resource_url') or data.get('uri') or f"https://www.discogs.com/release/{data.get('id')}",
                'notes':data.get('notes')
            })
    
        df = pd.DataFrame(rows)
    
        if selected_cols:
            df = df[[col for col in selected_cols if col in df.columns]]
    
        os.makedirs("output", exist_ok=True)
        path = f"output/{data['id']}_release.csv"
        df.to_csv(f"output/{data['id']}_release.csv", index=False)
    
        if return_df:
            return df
        return path

            
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
                df = self.parsing_release_lists(release_data, return_df=True)
                # Add a blank row at the end of this release
                blank_row = pd.DataFrame([[""] * df.shape[1]], columns=df.columns)
                df = pd.concat([df, blank_row], ignore_index=True)
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
