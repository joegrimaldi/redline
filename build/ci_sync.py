#!/usr/bin/env python3
"""GitHub Actions Strava sync: refresh token -> pull all Walk activities with polylines
-> write polys_life.txt, strava_meta.tsv, walk_dates.txt (in this build/ dir).
Env: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN."""
import os, json, urllib.request, urllib.parse, sys

CID = os.environ['STRAVA_CLIENT_ID']
SEC = os.environ['STRAVA_CLIENT_SECRET']
RT  = os.environ['STRAVA_REFRESH_TOKEN']

def post(url, fields):
    data = urllib.parse.urlencode(fields).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as r:
        return json.load(r)

def get(url, token):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

# 1) refresh access token
tok = post('https://www.strava.com/oauth/token', {
    'client_id': CID, 'client_secret': SEC,
    'refresh_token': RT, 'grant_type': 'refresh_token'})
AT = tok['access_token']
print('token refreshed; expires', tok.get('expires_at'))

# 2) pull all activities (paginated)
acts = []
for page in range(1, 21):
    arr = get('https://www.strava.com/api/v3/athlete/activities?per_page=100&page=%d' % page, AT)
    if not arr:
        break
    acts += arr
print('activities fetched:', len(acts))

# 3) keep Walk activities that have a polyline
poly, meta, dates = [], [], set()
for a in acts:
    st = a.get('sport_type') or a.get('type')
    if st != 'Walk':
        continue
    m = a.get('map') or {}
    pl = m.get('summary_polyline')
    if not pl:
        continue
    wid = str(a['id'])
    d = (a.get('start_date_local') or a.get('start_date') or '')[:10]
    dist = a.get('distance', 0) or 0
    if not d:
        continue
    poly.append(wid + ' ' + pl)
    meta.append('%s\t%s\t%s' % (wid, d, dist))
    dates.add(d)

if not poly:
    print('WARNING: no walks with polylines pulled; leaving existing files untouched')
    sys.exit(0)

meta.sort(key=lambda x: x.split('\t')[1])
open('polys_life.txt', 'w').write('\n'.join(poly) + '\n')
open('strava_meta.tsv', 'w').write('\n'.join(meta) + '\n')
open('walk_dates.txt', 'w').write('\n'.join(sorted(dates)) + '\n')
print('wrote %d walks across %d days' % (len(poly), len(dates)))
