# ---- island mask: what counts as Manhattan for the denominator ----
# Streets come from the Manhattan borough area, so they only need the name rule (bridges that leave
# the island, highways, tunnels). Park/plaza paths were fetched by bounding box and leak into NJ,
# Queens and Brooklyn, so a path must ALSO sit inside a neighborhood polygon (neighborhoods.json,
# which includes Roosevelt Island, Randall's Island, Marble Hill and Governors Island) or come within
# HOOD_M of a hood polygon's edge, or within NEAR_M of a street node (waterfront esplanades, piers and
# Little Island lie just outside the hood polygons; the Bronx, Queens and NJ are 130 m+ away).
import re, json, math, os
NOROUTE=re.compile(r"\b(FDR Drive|Harlem River Drive|Henry Hudson Parkway|West Side Highway|Expressway|Tunnel)\b"
                   r"|Hoboken|Newport|Roosevelt Island Bridge|Queens Plaza|Pulaski"
                   r"|^(Manhattan|Brooklyn|Williamsburg|Washington|Madison Avenue|Willis Avenue|Third Avenue|145th Street"
                   r"|Macombs Dam|University Heights|(Ed Koch )?Queensboro|Triborough|RFK|Robert F\.? Kennedy|George Washington"
                   r"|Alexander Hamilton|High) Bridge\b", re.I)
NEAR_M=60.0; HOOD_M=90.0
def _pip(lat,lon,ring):
    inside=False; j=len(ring)-1
    for i in range(len(ring)):
        yi,xi=ring[i][0],ring[i][1]; yj,xj=ring[j][0],ring[j][1]
        if (yi>lat)!=(yj>lat) and lon<(xj-xi)*(lat-yi)/((yj-yi) or 1e-12)+xi: inside=not inside
        j=i
    return inside
class IslandMask:
    def __init__(self, hoods_path, street_nodes):
        self.hoods=json.load(open(hoods_path)) if os.path.exists(hoods_path) else []
        self.cell=0.0006; self.grid={}
        for la,lo in street_nodes:
            self.grid.setdefault((int(la/self.cell),int(lo/self.cell)),[]).append((la,lo))
    def in_hood(self,lat,lon):
        for h in self.hoods:
            b=h['bb']
            if lat<b[0] or lat>b[2] or lon<b[1] or lon>b[3]: continue
            for r in h['r']:
                if _pip(lat,lon,r): return True
        return False
    def near_hood(self,lat,lon):
        k=math.cos(math.radians(lat)); pad=0.0012
        for h in self.hoods:
            b=h['bb']
            if lat<b[0]-pad or lat>b[2]+pad or lon<b[1]-pad or lon>b[3]+pad: continue
            for r in h['r']:
                for i in range(len(r)):
                    a=r[i]; c=r[(i+1)%len(r)]
                    x,y=lon*111320*k,lat*110540; x1,y1=a[1]*111320*k,a[0]*110540; x2,y2=c[1]*111320*k,c[0]*110540
                    dx,dy=x2-x1,y2-y1; L2=dx*dx+dy*dy; t=((x-x1)*dx+(y-y1)*dy)/L2 if L2 else 0.0; t=max(0.0,min(1.0,t))
                    if math.hypot(x-(x1+t*dx),y-(y1+t*dy))<=HOOD_M: return True
        return False
    def near_street(self,lat,lon):
        ca,co=int(lat/self.cell),int(lon/self.cell); k=math.cos(math.radians(lat))
        for da in (-1,0,1):
            for do in (-1,0,1):
                for la,lo in self.grid.get((ca+da,co+do),()):
                    if math.hypot((la-lat)*110540,(lo-lon)*111320*k)<=NEAR_M: return True
        return False
    def keep_path(self,name,pts):
        if NOROUTE.search(name or ''): return False
        return any(self.in_hood(la,lo) or self.near_street(la,lo) or self.near_hood(la,lo) for la,lo in pts)
