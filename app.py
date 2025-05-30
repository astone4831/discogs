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

@app.route("/search_artist_release")
def search_artist_release():
    q = request.args.get("q", "").strip()
    # require at least one space to split artist + release
    if " " not in q:
        return jsonify([])

    artist_part, release_part = q.split(" ", 1)

    try:
        results = dc.search_artist_and_release(artist_part, release_part)
        return jsonify(results)      # 200 OK + [] or [ {...}, ... ]
    except Exception as e:
        app.logger.error("search_artist_release failed", exc_info=e)
        return jsonify([])           # still 200 OK + []

@app.route('/label_releases')
def label_releases():
    label_id = request.args.get('id')
    if not label_id:
        return jsonify({'error': 'No label ID provided'}), 400
    data = dc.get_all_label_release(label_id)
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
    cols_param = request.args.get('cols')
    if not release_id:
        return jsonify({'error': 'No release ID provided'}), 400
    selected_cols = cols_param.split(',') if cols_param else []
    try:
        data = dc.get_release(release_id)
        file_path = dc.parsing_release_lists(data, return_df=False, selected_cols=selected_cols)
    except Exception as e:
        print(f"ERROR: {e}")
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
    # Pre-check version count
    try:
        r = requests.get(f"https://api.discogs.com/masters/{master_id}/versions?per_page=1", headers=dc.headers)
        if r.status_code != 200:
            return jsonify({'error': 'Invalid master ID or Discogs error'}), 400
        total_versions = r.json().get('pagination', {}).get('items', 0)
        if total_versions > 200:
            return jsonify({'warning': f'This master has {total_versions} versions. Are you sure you want to download them all?'}), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    try:
        file_path = dc.export_master_release_details_csv(master_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return send_file(file_path, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port = 10000)
