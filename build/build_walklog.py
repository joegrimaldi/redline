import json,math,collections
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
CELL=10.0
G=json.load(open('graph.json')); N=G['nodes']; E=G['edges']
def hav(a,b):
    la1,lo1=N[a]; la2,lo2=N[b]
    x1,y1=proj(la1,lo1); x2,y2=proj(la2,lo2)
    return math.hypot(x2-x1,y2-y1)
# precompute edge sample cells + length
edgeCells=[]; edgeLen=[]
cellToEdges=collections.defaultdict(list)
for i,e in enumerate(E):
    ax,ay=proj(*N[e[0]]); bx,by=proj(*N[e[1]])
    L=math.hypot(bx-ax,by-ay); edgeLen.append(L)
    st=max(1,int(L/8)); cells=set()
    for k in range(st+1):
        t=k/st; x=ax+(bx-ax)*t; y=ay+(by-ay)*t
        cells.add((int(x//CELL),int(y//CELL)))
    cells=list(cells); edgeCells.append(cells)
    for c in cells: cellToEdges[c].append(i)
off=[(dx,dy) for dx in(-2,-1,0,1,2) for dy in(-2,-1,0,1,2) if (dx*dx+dy*dy)*100<=400]
# meta + polylines
meta={}
for line in open('strava_meta.tsv'):
    p=line.strip().split('\t')
    if len(p)>=3: meta[p[0]]=(p[1],float(p[2]))
poly={}
for line in open('polys_life.txt'):
    line=line.strip()
    if not line: continue
    sp=line.split(' ',1)
    if len(sp)==2: poly[sp[0]]=sp[1]
# order ids by date (only those we have polyline + meta for)
ids=[i for i in poly if i in meta]
ids.sort(key=lambda i: meta[i][0])
visitedExp=set(); covered=[False]*len(E)
perwalk={}  # id -> newMi
for wid in ids:
    try: pts=decode(poly[wid])
    except: perwalk[wid]=0; continue
    pp=[proj(a,b) for a,b in pts]
    newExp=set()
    for (x1,y1),(x2,y2) in zip(pp,pp[1:]):
        dd=math.hypot(x2-x1,y2-y1)
        if dd>300: continue
        st=max(1,int(dd/5))
        for k in range(st+1):
            t=k/st; cx=int((x1+(x2-x1)*t)//CELL); cy=int((y1+(y2-y1)*t)//CELL)
            for dx,dy in off:
                c=(cx+dx,cy+dy)
                if c not in visitedExp:
                    visitedExp.add(c); newExp.add(c)
    # candidate edges touched by newly-expanded cells
    cand=set()
    for c in newExp:
        for ei in cellToEdges.get(c,()): cand.add(ei)
    nm=0.0
    for ei in cand:
        if covered[ei]: continue
        cells=edgeCells[ei]; hit=sum(1 for c in cells if c in visitedExp)
        if cells and hit/len(cells)>=0.5:
            covered[ei]=True; nm+=edgeLen[ei]
    perwalk[wid]=nm/1609.344
# aggregate per day
days=collections.defaultdict(lambda:[0,0.0,0.0])  # date->[nwalks,totalMi,newMi]
for wid in ids:
    d,dist=meta[wid]
    days[d][0]+=1; days[d][1]+=dist/1609.344; days[d][2]+=perwalk[wid]
out=sorted(days.items())
cum=0.0
with open('walk_log.txt','w') as f:
    for d,(nw,tot,new) in out:
        cum+=new
        f.write(f"{d}\t{nw}\t{tot:.2f}\t{new:.2f}\t{cum:.1f}\n")
totNew=sum(v[2] for v in days.values()); totMi=sum(v[1] for v in days.values())
print(f"walks matched {len(ids)} | days {len(days)} | total walked {totMi:.0f}mi | new-redlined sum {totNew:.1f}mi")
print("first days:", out[0][0], "->", out[-1][0])
