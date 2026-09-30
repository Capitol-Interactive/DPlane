#!/usr/bin/env python3
"""Upload Asana-hosted attachments to Plane work items and add Google Drive links to descriptions. Idempotent.
usage: migrate_attachments.py [--apply]. Token read at run time from the uploaded secret-key CSV, never printed.
Asana download URLs are temporary; they are read from urls.json (scratchpad only, never committed)."""
import csv,glob,json,sys,time,uuid,urllib.request,urllib.error,html
APPLY="--apply" in sys.argv
tok=list(csv.DictReader(open(sorted(glob.glob("/root/.claude/uploads/3d6a31d2-643f-5caf-9b3a-bd04549d1398/*secret-key*.csv"))[-1])))[0]["Secret key"].strip()
API="https://api.destinationpass.dev/api/v1/workspaces/destination-pass"
FLOW="45f52c84-ce0a-4de6-a75c-822156a61f2b"; SALES="24d7c935-1efc-4cf2-8947-ef61ff785420"
FILES=[ # attachment gid, project, issue, name, size
 ("1213139974411695",FLOW,"9d14bd59-51c4-4108-bf19-ff551a66d5c6","image.png",194680),
 ("1213139974411702",FLOW,"9d14bd59-51c4-4108-bf19-ff551a66d5c6","Screenshot 2026-02-05 at 3.58.47 PM.png",194565),
 ("1213125487414217",FLOW,"570f37a4-65f9-4697-a090-1e7e042440dc","image.png",247540),
 ("1213139974411698",FLOW,"2f8fd055-bf57-40e1-9a95-2595ec1068e6","image.png",75376),
 ("1213139974411700",FLOW,"2f8fd055-bf57-40e1-9a95-2595ec1068e6","Screenshot 2026-02-05 at 4.01.42 PM.png",75889),
]
LINKS=[(SALES,"36b65fb2-38b7-46a5-b73d-44116655ad1d","Streamlined DP Pitch Deck","https://docs.google.com/presentation/d/1_TE854gNXXF-Wy_6EZ6rzkXvlZk1T-n1B3QVJlx04E8/edit"),
       (SALES,"98583325-5f94-4bf8-8519-0d18ecfd440b","Destination Pass Discovery Script","https://docs.google.com/document/d/12TOZ0IS8Cj5eljWb8k7sRRRbTtMuWQ-JVjFuQfdB-Ps/edit")]
urls=json.load(open("urls.json"))
_l=[0.0]
def call(m,p,b=None,raw=False):
    w=1.15-(time.time()-_l[0]); time.sleep(max(w,0)); _l[0]=time.time()
    r=urllib.request.Request(API+p,method=m,data=None if b is None else json.dumps(b).encode(),headers={"X-API-Key":tok,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(r,timeout=60) as x:
            d=x.read(); return x.status,d if raw else (json.loads(d) if d else {})
    except urllib.error.HTTPError as e: return e.code,e.read().decode()[:300]
print("mode","APPLY" if APPLY else "DRY-RUN")
for gid,pid,iid,name,size in FILES:
    s,ex=call("GET",f"/projects/{pid}/issues/{iid}/issue-attachments/")
    have=[a for a in (ex if isinstance(ex,list) else ex.get("results",[])) if isinstance(a,dict) and a.get("attributes",{}).get("name")==name and a.get("attributes",{}).get("size")==size] if s==200 else []
    if have: print("already there",name,iid[:8]); continue
    if gid not in urls: print("NO URL",gid,name); continue
    if not APPLY: print("would upload",name,size,"->",iid[:8]); continue
    data=urllib.request.urlopen(urllib.request.Request(urls[gid]),timeout=60).read()
    assert len(data)==size,f"size mismatch {name}: {len(data)} vs {size}"
    ctype="image/png" if name.lower().endswith(".png") else "image/jpeg"
    s,a=call("POST",f"/projects/{pid}/issues/{iid}/issue-attachments/",{"name":name,"type":ctype,"size":size})
    assert s in(200,201),(s,a)
    u=a["upload_data"]; b="----x"+uuid.uuid4().hex; body=b""
    for k,v in u["fields"].items(): body+=f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body+=f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{uuid.uuid4().hex}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()+data+f"\r\n--{b}--\r\n".encode()
    with urllib.request.urlopen(urllib.request.Request(u["url"],method="POST",data=body,headers={"Content-Type":f"multipart/form-data; boundary={b}"}),timeout=60) as x: up=x.status
    s2,_=call("PATCH",f"/projects/{pid}/issues/{iid}/issue-attachments/{a['asset_id']}/",{})
    print("uploaded",name,"bucket",up,"finalize",s2)
for pid,iid,name,url in LINKS:
    s,cur=call("GET",f"/projects/{pid}/issues/{iid}/")
    if url in (cur.get("description_html") or ""): print("link already there",name); continue
    if not APPLY: print("would add link",name); continue
    add=f'<p>Attachment from Asana (Google Drive): <a href="{html.escape(url)}">{html.escape(name)}</a></p>'
    s,_=call("PATCH",f"/projects/{pid}/issues/{iid}/",{"description_html":(cur.get("description_html") or "")+add}); print("link added",name,s)
