import sys, json, csv, os
from pathlib import Path
from flask import Flask, request, Response

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

def _j(data, status=200):
    return Response(json.dumps(data, ensure_ascii=False, default=str),
                    status=status, mimetype="application/json")

def _load(name):
    path = DATA_DIR / name
    if not path.exists():
        return []
    rows = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({k: (v if v is not None else "") for k, v in row.items()})
    except Exception as e:
        pass
    return rows

_S = _load("startups.csv")
_P = _load("products.csv")
_PA = _load("research_papers.csv")
_J = _load("jobs.csv")
_N = _load("news.csv")
_M = _load("entity_mapping_log.csv")

def _n(v, d=0):
    try: return float(v) if v not in (None,"") else d
    except: return d

@app.route("/api/health")
def health():
    return _j({"ok":True,"startups":len(_S),"products":len(_P),"papers":len(_PA),"jobs":len(_J),"news":len(_N),"data_dir":str(DATA_DIR),"exists":DATA_DIR.exists()})

@app.route("/api/stats")
def stats():
    avg = round(sum(_n(m.get("confidence_score"),0.9) for m in _M)/max(1,len(_M)),3)
    return _j({"startups_count":len(_S),"products_count":len(_P),"papers_count":len(_PA),"jobs_count":len(_J),"news_count":len(_N),"mappings_count":len(_M),"total_records":len(_S)+len(_P)+len(_PA)+len(_J)+len(_N),"avg_confidence":avg,"excel_available":(DATA_DIR/"output_intelligence_graph.xlsx").exists(),"pdf_available":(PROJECT_ROOT/"architecture.pdf").exists()})

@app.route("/api/startups")
def startups():
    q=request.args.get("search","").lower(); ind=request.args.get("industry","").strip().lower()
    ts=request.args.get("team_size","").strip(); sb=request.args.get("sort_by","").strip().lower()
    lim=request.args.get("limit",""); items=list(_S)
    if ind and ind!="all": items=[s for s in items if ind in s.get("industry","").lower()]
    if ts and ts!="all":
        def _t(s):
            try: e=float(s.get("content.data.employeeCount") or -1)
            except: e=-1
            if ts=="1-5": return 1<=e<=5
            if ts=="6-15": return 6<=e<=15
            if ts=="16-50": return 16<=e<=50
            if ts=="50+": return e>50
            if ts=="undisclosed": return e<=0
            return True
        items=[s for s in items if _t(s)]
    if q: items=[s for s in items if q in s.get("content.entityName","").lower() or q in s.get("industry","").lower() or q in s.get("description","").lower()]
    if sb=="team_desc": items.sort(key=lambda s:_n(s.get("content.data.employeeCount"),-1),reverse=True)
    elif sb=="team_asc": items.sort(key=lambda s:_n(s.get("content.data.employeeCount"),999999))
    elif sb=="name": items.sort(key=lambda s:s.get("content.entityName","").lower())
    total=len(items)
    if lim and lim.isdigit() and int(lim)>0: items=items[:int(lim)]
    return _j({"total":total,"data":items})

@app.route("/api/products")
def products():
    q=request.args.get("search","").lower(); pr=request.args.get("pricing","").upper()
    lim=request.args.get("limit",""); items=list(_P)
    if pr and pr!="ALL": items=[p for p in items if p.get("content.pricingModel","")==pr]
    if q: items=[p for p in items if q in p.get("product_name","").lower() or q in p.get("content.startupName","").lower()]
    total=len(items)
    if lim and lim.isdigit() and int(lim)>0: items=items[:int(lim)]
    return _j({"total":total,"data":items})

@app.route("/api/papers")
def papers():
    q=request.args.get("search","").lower(); hc=request.args.get("has_code","").lower()
    src=request.args.get("source","").strip(); sb=request.args.get("sort_by","impact").lower()
    lim=request.args.get("limit",""); items=list(_PA)
    if hc=="true": items=[p for p in items if p.get("content.github_url","").strip()]
    elif hc=="false": items=[p for p in items if not p.get("content.github_url","").strip()]
    if src and src.upper()!="ALL": items=[p for p in items if src.lower() in p.get("content.source_platform","").lower()]
    if q: items=[p for p in items if q in p.get("content.title","").lower() or q in p.get("content.authors","").lower()]
    if sb=="stars": items.sort(key=lambda p:_n(p.get("content.github_stars")),reverse=True)
    elif sb=="upvotes": items.sort(key=lambda p:_n(p.get("content.huggingface_upvotes")),reverse=True)
    elif sb=="date": items.sort(key=lambda p:p.get("content.published_date",""),reverse=True)
    else: items.sort(key=lambda p:(_n(p.get("content.impact_score")),_n(p.get("content.github_stars"))),reverse=True)
    total=len(items); twc=sum(1 for p in _PA if p.get("content.github_url","").strip())
    if lim and lim.isdigit() and int(lim)>0: items=items[:int(lim)]
    return _j({"total":total,"total_with_code":twc,"data":items})

@app.route("/api/jobs")
def jobs():
    q=request.args.get("search","").lower(); role=request.args.get("role","")
    items=list(_J)
    if role and role!="ALL": items=[j for j in items if role.lower() in j.get("content.role_family","").lower()]
    if q: items=[j for j in items if q in j.get("title","").lower() or q in j.get("content.company","").lower()]
    return _j({"total":len(items),"data":items})

@app.route("/api/news")
def news():
    q=request.args.get("search","").lower(); src=request.args.get("source","")
    items=list(_N)
    if src and src!="ALL": items=[n for n in items if src.lower() in n.get("source.name","").lower()]
    if q: items=[n for n in items if q in n.get("content.title","").lower()]
    return _j({"total":len(items),"data":items})

@app.route("/api/mappings")
def mappings():
    q=request.args.get("search","").lower(); lim=request.args.get("limit",""); items=list(_M)
    if q: items=[m for m in items if q in m.get("raw_name","").lower() or q in m.get("canonical_name","").lower()]
    total=len(items)
    if lim and lim.isdigit() and int(lim)>0: items=items[:int(lim)]
    return _j({"total":total,"data":items})

@app.route("/api/resolve", methods=["POST"])
def resolve():
    try:
        body=request.get_json(force=True) or {}; raw=(body.get("name") or "").strip()
        if not raw: return _j({"error":"Empty name"},400)
        names=[s.get("content.entityName","") for s in _S if s.get("content.entityName")]
        best=None; best_score=0
        rl=raw.lower()
        for n in names:
            nl=n.lower()
            if nl==rl: return _j({"raw_name":raw,"canonical_name":n,"confidence":1.0,"method":"exact","is_known":True})
            common=sum(1 for c in rl if c in nl); score=common/max(len(rl),len(nl))
            if score>best_score: best_score=score; best=n
        if best and best_score>0.7: return _j({"raw_name":raw,"canonical_name":best,"confidence":round(best_score,3),"method":"fuzzy","is_known":True})
        return _j({"raw_name":raw,"canonical_name":raw,"confidence":0.0,"method":"passthrough","is_known":False})
    except Exception as e:
        return _j({"error":str(e)},500)

@app.route("/api/pipeline/status")
def pl_status(): return _j({"sources":[],"recent_runs":[],"total_sources":0})

@app.route("/api/pipeline/logs")
def pl_logs(): return _j({"runs":[]})

@app.route("/api/pipeline/run-now", methods=["POST"])
def pl_run(): return _j({"status":"serverless-only"})

@app.route("/api/trigger", methods=["POST"])
def trigger(): return _j({"status":"serverless-only"})

@app.route("/api/graph/entities")
def graph_entities():
    cat=request.args.get("type","startups").lower(); result=[]; seen=set()
    if cat in ("product","products"):
        for p in _P:
            n=p.get("product_name","").strip()
            if n and n not in seen: seen.add(n); result.append({"name":n,"source":p.get("content.startupName","Product")})
    elif cat in ("paper","papers"):
        for p in _PA:
            t=p.get("content.title","").strip()
            if t and t not in seen: seen.add(t); result.append({"name":t,"source":f"{p.get('content.github_stars',0)} Stars"})
    elif cat in ("job","jobs"):
        for j in _J:
            t=j.get("title","").strip()
            if t and t not in seen: seen.add(t); result.append({"name":t,"source":j.get("content.company","Job")})
    elif cat in ("news","news_signals"):
        for n in _N:
            t=n.get("content.title","").strip()
            if t and t not in seen: seen.add(t); result.append({"name":t,"source":n.get("source.name","News")})
    else:
        for s in _S:
            n=s.get("content.entityName","").strip()
            if n and n not in seen: seen.add(n); result.append({"name":n,"source":s.get("industry","Startup"),"is_seed":False})
        result.sort(key=lambda x:x["name"])
    return _j({"total":len(result),"entities":result[:300]})

@app.route("/api/graph/entity")
def graph_entity():
    raw=request.args.get("name","").strip(); etype=request.args.get("type","startups").lower()
    if not raw: return _j({"error":"name required"},400)
    sd=next((s for s in _S if s.get("content.entityName","").lower()==raw.lower()),{})
    if not sd: sd=next((s for s in _S if raw.lower() in s.get("content.entityName","").lower()),{})
    canon=sd.get("content.entityName",raw); url=sd.get("content.data.website","") or sd.get("source.url","")
    nodes=[{"id":"c","label":canon,"group":"startup","title":"","url":url or "#","value":40,"shape":"ellipse","color":{"background":"#6366F1","border":"#A5B4FC"},"font":{"color":"#fff","size":15},"meta":{"type":"Startup","name":canon}}]
    edges=[]
    for i,p in enumerate([p for p in _P if p.get("content.startupName","").lower()==canon.lower()][:4]):
        nodes.append({"id":f"p{i}","label":p.get("product_name",""),"group":"product","title":"","url":p.get("source.url","") or url,"value":22,"shape":"dot","color":{"background":"#059669","border":"#34D399"},"font":{"color":"#ECFDF5","size":11},"meta":{"type":"Product"}})
        edges.append({"from":"c","to":f"p{i}","label":"BUILDS","color":{"color":"#059669"},"length":150})
    for i,j in enumerate([j for j in _J if canon.lower() in j.get("content.company","").lower()][:3]):
        nodes.append({"id":f"j{i}","label":j.get("title","")[:24],"group":"job","title":"","url":j.get("job_url","") or url,"value":18,"shape":"dot","color":{"background":"#0284C7","border":"#7DD3FC"},"font":{"color":"#F0F9FF","size":11},"meta":{"type":"Job"}})
        edges.append({"from":"c","to":f"j{i}","label":"HIRING","color":{"color":"#0284C7"},"length":170})
    for i,n in enumerate([n for n in _N if canon.lower() in n.get("content.title","").lower()][:3]):
        nodes.append({"id":f"n{i}","label":n.get("content.title","")[:25],"group":"news","title":"","url":n.get("source.url","") or url,"value":18,"shape":"dot","color":{"background":"#F43F5E","border":"#FECDD3"},"font":{"color":"#FFF1F2","size":11},"meta":{"type":"News"}})
        edges.append({"from":"c","to":f"n{i}","label":"SIGNAL","color":{"color":"#F43F5E"},"length":200})
    return _j({"canonical_name":canon,"entity_type":etype,"startup":sd,"nodes":nodes,"edges":edges,"counts":{"total_nodes":len(nodes),"total_edges":len(edges)}})
