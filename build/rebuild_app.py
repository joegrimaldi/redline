#!/usr/bin/env python3
"""Redline rebuild driver — run from the redline-build/ folder.
Inputs (same folder): ways.json, waytype.json, tags.json, polys_life.txt, head.html, tail.html, sw.js
Outputs: graph.json (here) + ../redline-app/index.html + ../redline-app/sw.js (cache version bumped)
Prints stats incl. % of island redlined. Re-fetching OSM is NOT needed (streets are static)."""
import json, math, os, re

HERE=os.path.dirname(os.path.abspath(__file__))
def P(f): return os.path.join(HERE,f)
APP=os.path.normpath(os.path.join(HERE,'..','redline-app'))

lat0=math.radians(40.78); MLON=111320*math.cos(lat0); MLAT=110540
def proj(la,lo): return (lo*MLON, la*MLAT)
def decode(s):
    pts=[];i=0;lat=0;lng=0;n=len(s)
    while i<n:
        for j in range(2):
            sh=0;res=0
            while True:
                b=ord(s[i])-63;i+=1;res|=(b&0x1f)<<sh;sh+=5
                if b<0x20:break
            d=~(res>>1) if (res&1) else (res>>1)
            if j==0:lat+=d
            else:lng+=d
        pts.append((lat*1e-5,lng*1e-5))
    return pts

# visited cells from lifetime traces (+ walk stats)
CELL=10.0; visited=set()
walks=0; totwalk=0.0; longest=0.0
for line in open(P('polys_life.txt')):
    line=line.strip()
    if not line: continue
    try: pts=decode(line.split(' ',1)[1])
    except: continue
    pp=[proj(a,b) for a,b in pts]
    walks+=1; tl=0.0
    for (x1,y1),(x2,y2) in zip(pp,pp[1:]):
        dd=math.hypot(x2-x1,y2-y1)
        if dd>300: continue
        tl+=dd
        st=max(1,int(dd/5))
        for k in range(st+1):
            t=k/st; visited.add((int((x1+(x2-x1)*t)//CELL),int((y1+(y2-y1)*t)//CELL)))
    totwalk+=tl; longest=max(longest,tl)
off=[(dx,dy) for dx in(-2,-1,0,1,2) for dy in(-2,-1,0,1,2) if (dx*dx+dy*dy)*100<=400]
def cov(x,y):
    cx,cy=int(x//CELL),int(y//CELL)
    return any((cx+dx,cy+dy) in visited for dx,dy in off)

ways=json.load(open(P('ways.json'))); wtype=json.load(open(P('waytype.json')))
tags={str(e['id']):e.get('tags',{}).get('name','') for e in json.load(open(P('tags.json')))['elements']}
EXCL={'motorway','trunk','pedestrian'}
def k6(p): return (round(p['lat'],6),round(p['lon'],6))
import collections
freq=collections.Counter(); inc=[]
for wid,g in ways.items():
    if wtype.get(str(wid),'?') in EXCL or len(g)<2: continue
    inc.append((wid,g))
    for p in g: freq[k6(p)]+=1
isnode=set()
for wid,g in inc: isnode.add(k6(g[0])); isnode.add(k6(g[-1]))
for c,f in freq.items():
    if f>=2: isnode.add(c)
nodeid={}; nodes=[]
def nid(c):
    if c not in nodeid: nodeid[c]=len(nodes); nodes.append([round(c[0],5),round(c[1],5)])
    return nodeid[c]
nameidx={}; names=[]
def nmid(nm):
    if nm not in nameidx: nameidx[nm]=len(names); names.append(nm)
    return nameidx[nm]
edges=[]; seen=set()
def subcov(sub):
    ns=0;nc=0
    for a,b in zip(sub,sub[1:]):
        ax,ay=proj(a['lat'],a['lon']);bx,by=proj(b['lat'],b['lon'])
        d=math.hypot(bx-ax,by-ay);st=max(1,int(d/8))
        for kk in range(st+1):
            ns+=1
            if cov(ax+(bx-ax)*kk/st,ay+(by-ay)*kk/st):nc+=1
    return (nc/ns)>=0.5 if ns else False
for wid,g in inc:
    nm=tags.get(str(wid),'') or '(unnamed)'; nmi=nmid(nm)
    cur=[g[0]]; startc=k6(g[0])
    for p in g[1:]:
        cur.append(p); c=k6(p)
        if c in isnode:
            a=nid(startc); b=nid(c)
            if a!=b:
                ek=(min(a,b),max(a,b))
                if ek not in seen:
                    seen.add(ek); edges.append([a,b,nmi,1 if subcov(cur) else 0])
            startc=c; cur=[p]
hx,hy=proj(40.70435,-74.00985)
home=min(range(len(nodes)),key=lambda i:(nodes[i][1]*MLON-hx)**2+(nodes[i][0]*MLAT-hy)**2)
json.dump({'nodes':nodes,'names':names,'edges':edges,'home':home}, open(P('graph.json'),'w'), separators=(',',':'))

# island % redlined (edge-length weighted)
def el(a,b):
    return math.hypot((nodes[b][1]-nodes[a][1])*MLON,(nodes[b][0]-nodes[a][0])*MLAT)
tot=sum(el(e[0],e[1]) for e in edges); covl=sum(el(e[0],e[1]) for e in edges if e[3]==1)
pct=100*covl/tot if tot else 0
segsDone=sum(1 for e in edges if e[3]==1)

# ---- neighborhood conquest (approx bounding boxes, downtown-first) ----
HOODS=[('Battery Park City',40.700,-74.022,40.720,-74.013),('Financial District',40.701,-74.015,40.710,-74.003),
 ('Seaport / Civic Center',40.706,-74.004,40.715,-73.997),('Tribeca',40.714,-74.016,40.724,-74.002),
 ('Chinatown',40.712,-74.002,40.721,-73.991),('Lower East Side',40.712,-73.991,40.723,-73.974),
 ('SoHo / Nolita',40.720,-74.006,40.727,-73.991),('West Village',40.727,-74.014,40.741,-74.000),
 ('East Village',40.722,-73.992,40.733,-73.972),('Chelsea',40.740,-74.012,40.756,-73.995),
 ('Flatiron / Gramercy',40.733,-73.999,40.745,-73.978),('Murray Hill / Kips Bay',40.743,-73.984,40.756,-73.970),
 ('Midtown',40.752,-74.002,40.766,-73.972),("Hell's Kitchen",40.756,-74.004,40.773,-73.986),
 ('Upper East Side',40.760,-73.972,40.792,-73.946),('Upper West Side',40.770,-73.992,40.802,-73.956),
 ('Harlem / Morningside',40.792,-73.968,40.835,-73.930),('Washington Hts / Inwood',40.835,-73.948,40.882,-73.902)]
hagg={h[0]:[0,0] for h in HOODS}  # name -> [doneSeg, totSeg]
for e in edges:
    mla=(nodes[e[0]][0]+nodes[e[1]][0])/2; mlo=(nodes[e[0]][1]+nodes[e[1]][1])/2
    for nm,s,w,n,ee in HOODS:
        if s<=mla<=n and w<=mlo<=ee:
            hagg[nm][1]+=1;
            if e[3]==1: hagg[nm][0]+=1
            break
hoods=[{'name':nm,'done':v[0],'tot':v[1],'pct':round(100*v[0]/v[1],1) if v[1] else 0} for nm,v in hagg.items() if v[1]>=10]
hoods.sort(key=lambda x:(-x['pct'],x['name']))

# ---- streak + calendar from walk_dates.txt ----
import datetime
try: dset=set(d.strip() for d in open(P('walk_dates.txt')) if d.strip())
except: dset=set()
today=datetime.date.today()
def hasd(d): return d.isoformat() in dset
streak=0; curd=today if hasd(today) else today-datetime.timedelta(days=1)
while hasd(curd): streak+=1; curd-=datetime.timedelta(days=1)
cal=[(1 if hasd(today-datetime.timedelta(days=k)) else 0) for k in range(34,-1,-1)]

STATS={'pctRedlined':round(pct,1),'coveredMi':round(covl/1609.344,1),'totalMi':round(tot/1609.344,1),
       'segsDone':segsDone,'segsTotal':len(edges),'walks':walks,
       'totalWalkedMi':round(totwalk/1609.344,1),'longestMi':round(longest/1609.344,1),
       'hoods':hoods,'streak':streak,'walkDays':len(dset),'cal':cal,'todayWalked':hasd(today)}
print(f"nodes {len(nodes)} edges {len(edges)} | covered {covl/1609.344:.1f}/{tot/1609.344:.1f} mi = {pct:.1f}% redlined | walks {walks} totWalked {totwalk/1609.344:.0f}mi longest {longest/1609.344:.1f}mi")

# walk log (per-day) + per-walk distances for calendar & charts
WALKLOG=[]
try:
    for line in open(P('walk_log.txt')):
        p=line.strip().split('\t')
        if len(p)>=5: WALKLOG.append([p[0],int(p[1]),float(p[2]),float(p[3]),float(p[4])])
except Exception: pass
WALKMI=[]
try:
    for line in open(P('strava_meta.tsv')):
        p=line.strip().split('\t')
        if len(p)>=3: WALKMI.append(round(float(p[2])/1609.344,2))
except Exception: pass

# compute the next sw cache version first, so we can stamp it into the page
sw=open(P('sw.js')).read()
m=re.search(r"redline-v(\d+)",sw); v=int(m.group(1))+1 if m else 8
# assemble public index.html (address-stripped, version-stamped)
head=open(P('head.html')).read(); tail=open(P('tail.html')).read()
idx=head+'const G='+json.dumps({'nodes':nodes,'names':names,'edges':edges,'home':home},separators=(',',':'))+';\nconst STATS='+json.dumps(STATS)+';\nconst HOODBOX='+json.dumps([[h[0],h[1],h[2],h[3],h[4]] for h in HOODS])+';\nconst WALKLOG='+json.dumps(WALKLOG)+';\nconst WALKMI='+json.dumps(WALKMI)+';\n'+tail
for a,b in [('82 Beaver St','Start (home)'),('🏠 82 Beaver','🏠 Home'),('using 82 Beaver','using home base'),('__VER__','v%d'%v)]:
    idx=idx.replace(a,b)
os.makedirs(APP,exist_ok=True)
open(os.path.join(APP,'index.html'),'w').write(idx)
# write sw with bumped cache version
sw=re.sub(r"redline-v\d+","redline-v%d"%v,sw)
open(P('sw.js'),'w').write(sw); open(os.path.join(APP,'sw.js'),'w').write(sw)
print(f"wrote {APP}/index.html + sw.js (cache redline-v{v})")
