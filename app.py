from flask import Flask, jsonify, request, render_template, send_file
import requests
import discogs_api as dc
import os
import pandas as pd

app = Flask(__name__)
dc = dc.discogs()  # instantiate your class
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/release')
def release():
    release_id = request.args.get('id')
    if not release_id:
        return jsonify({'error': 'No release ID provided'}), 400
    
    data = dc.get_release(release_id)
    return jsonify(data)

@app.route('/artist_releases')
def artist_releases():
    artist_id = request.args.get('id')
    if not artist_id:
        return jsonify({'error': 'No artist ID provided'}), 400
    data = dc.artist_releases(artist_id)
    return jsonify(data)

@app.route('/env_check')
def env_check():
    return jsonify({
        "key": os.getenv('DISCOGS_KEY'),
        "secret": os.getenv('DISCOGS_SECRET')
    })

@app.route('/download_master_csv')
def download_master_csv():
    master_id = request.args.get('id')
    if not master_id:
        return jsonify({'error': 'No master ID provided'}), 400
    try:
        file_path = dc.export_master_versions_csv(master_id)
    except Exception as e:
        print("ERROR:", e)
        return jsonify({'error': str(e)}), 500
    return send_file(file_path, as_attachment=True)

@app.route('/download_csv')
def download_csv():
    release_id = request.args.get('id')
    if not release_id:
        return jsonify({'error': 'No release ID provided'}), 400
    try:
        release_data = dc.get_release(release_id)
        file_path = dc.parsing_release_lists(release_data)
        if not os.path.exists(file_path):
            raise Exception("CSV file not found after generation")
    except Exception as e:
        print("ERROR:", e)
        return jsonify({'error': str(e)}), 500
    return send_file(file_path, as_attachment=True)

@app.route('/download_artist_csv')
def download_artist_csv():
    artist_id = request.args.get('id')
    if not artist_id:
        return jsonify({'error': 'No artist ID provided'}), 400
    try:
        file_path = dc.export_artist_releases_csv(artist_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return send_file(file_path, as_attachment=True)

@app.route('/search_artist')
def search_artist():
    query = request.args.get('q')
    if not query:
        return jsonify([])
    url = "https://api.discogs.com/database/search"

    params = {
        "q": query,
        "type": "artist",
        "per_page":10,
        "key": dc.key,
        "secret": dc.secret
    }
    r = requests.get(url, params=params)
    results = r.json().get('results', [])
    # Clean response
    cleaned = [
        {"id": r['id'], "name": r['title']}
        for r in results if 'id' in r and 'title' in r
    ]
    return jsonify(cleaned)

@app.route('/download_master_deep_csv')
def download_master_deep_csv():
    master_id = request.args.get('id')
    if not master_id:
        return jsonify({'error': 'No master ID provided'}), 400
    try:
        file_path = dc.export_master_release_details_csv(master_id)
    except Exception as e:
        print("ERROR:", e)
        return jsonify({'error': str(e)}), 500
    return send_file(file_path, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port = 10000)
