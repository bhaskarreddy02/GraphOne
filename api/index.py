"""
Vercel WSGI entry point for GraphOne.
Standalone Flask app - imports ONLY pandas and flask (no src.* dependencies).
"""
import sys
import json
import os
from pathlib import Path
from flask import Flask, request, Response, send_file

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Load CSVs once at cold-start
# ---------------------------------------------------------------------------
def _load(name):
    path = DATA_DIR / name
    if not path.exists():
        return []
    try:
        import pandas as pd
        return pd.read_csv(path).fillna("").to_dict(orient="records")
    except Exception as e:
        return []

_startups  = _load("startups.csv")
_products  = _load("products.csv")
_papers    = _load("research_papers.csv")
_jobs      = _load("jobs.csv")
_news      = _load("news.csv")
_mappings  = _load("entity_mapping_log.csv")

def _json(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        status=status,
        mimetype="application/json"
    )

def _num(val, default=0):
    try:
        return float(val) if val is not None and str(val).strip() != "" else default
    except (ValueError, TypeError):
        return default


@app.route("/api/health")
def health():
    return _json({
        "status": "ok",
        "data_dir": str(DATA_DIR),
        "data_dir_exists": DATA_DIR.exists(),
        "records": {
            "startups": len(_startups),
            "products": len(_products),
            "papers":   len(_papers),
            "jobs":     len(_jobs),
            "news":     len(_news),
        }
    })


@app.route("/api/stats")
def stats():
    avg_conf = round(
        sum(float(m.get("confidence_score", 0.9)) for m in _mappings) / max(1, len(_mappings)), 3
    )
    return _json({
        "startups_count": len(_startups),
        "products_count": len(_products),
        "papers_count":   len(_papers),
        "jobs_count":     len(_jobs),
        "news_count":     len(_news),
        "mappings_count": len(_mappings),
        "total_records":  len(_startups)+len(_products)+len(_papers)+len(_jobs)+len(_news),
        "avg_confidence": avg_conf,
        "excel_available": (DATA_DIR / "output_intelligence_graph.xlsx").exists(),
        "pdf_available":   (PROJECT_ROOT / "architecture.pdf").exists(),
    })


@app.route("/api/startups")
def startups():
    query     = request.args.get("search", "").lower()
    industry  = request.args.get("industry", "").strip().lower()
    team_size = request.args.get("team_size", "").strip()
    sort_by   = request.args.get("sort_by", "").strip().lower()
    limit_p   = request.args.get("limit", "")
    items = list(_startups)
    if industry and industry != "all":
        items = [s for s in items if industry in str(s.get("industry","")).lower()]
    if team_size and team_size != "all":
        def _ts(s, ts):
            try: emp = float(s.get("content.data.employeeCount") or -1)
            except: emp = -1
            if ts=="1-5":   return 1<=emp<=5
            if ts=="6-15":  return 6<=emp<=15
            if ts=="16-50": return 16<=emp<=50
            if ts=="50+":   return emp>50
            if ts=="undisclosed": return emp<=0
            return True
        items = [s for s in items if _ts(s, team_size)]
    if query:
        items = [s for s in items if
                 query in str(s.get("content.entityName","")).lower() or
                 query in str(s.get("industry","")).lower() or
                 query in str(s.get("description","")).lower() or
                 query in str(s.get("content.data.location","")).lower()]
    if sort_by == "team_desc":
        items.sort(key=lambda s: _num(s.get("content.data.employeeCount"),-1), reverse=True)
    elif sort_by == "team_asc":
        items.sort(key=lambda s: _num(s.get("content.data.employeeCount"),999999))
    elif sort_by == "name":
        items.sort(key=lambda s: str(s.get("content.entityName","")).lower())
    total = len(items)
    if limit_p and limit_p.isdigit() and int(limit_p)>0:
        items = items[:int(limit_p)]
    return _json({"total": total, "data": items})


@app.route("/api/products")
def products():
    query   = request.args.get("search","").lower()
    pricing = request.args.get("pricing","").upper()
    limit_p = request.args.get("limit","")
    items = list(_products)
    if pricing and pricing != "ALL":
        items = [p for p in items if p.get("content.pricingModel")==pricing]
    if query:
        items = [p for p in items if
                 query in str(p.get("product_name","")).lower() or
                 query in str(p.get("content.startupName","")).lower()]
    total = len(items)
    if limit_p and limit_p.isdigit() and int(limit_p)>0:
        items = items[:int(limit_p)]
    return _json({"total": total, "data": items})


@app.route("/api/papers")
def papers():
    query    = request.args.get("search","").lower()
    has_code = request.args.get("has_code","").lower()
    source   = request.args.get("source","").strip()
    sort_by  = request.args.get("sort_by","impact").lower()
    limit_p  = request.args.get("limit","")
    items = list(_papers)
    if has_code=="true":
        items = [p for p in items if str(p.get("content.github_url","")).strip()]
    elif has_code=="false":
        items = [p for p in items if not str(p.get("content.github_url","")).strip()]
    if source and source.upper()!="ALL":
        items = [p for p in items if source.lower() in str(p.get("content.source_platform","")).lower()]
    if query:
        items = [p for p in items if
                 query in str(p.get("content.title","")).lower() or
                 query in str(p.get("content.authors","")).lower() or
                 query in str(p.get("content.abstract","")).lower()]
    if sort_by=="stars":
        items.sort(key=lambda p: _num(p.get("content.github_stars",0)), reverse=True)
    elif sort_by=="upvotes":
        items.sort(key=lambda p: _num(p.get("content.huggingface_upvotes",0)), reverse=True)
    elif sort_by=="date":
        items.sort(key=lambda p: str(p.get("content.published_date","")), reverse=True)
    else:
        items.sort(key=lambda p: (
            1 if str(p.get("content.github_url","")).strip() else 0,
            _num(p.get("content.impact_score",0)),
            _num(p.get("content.github_stars",0)),
            _num(p.get("content.huggingface_upvotes",0)),
            str(p.get("content.published_date",""))
        ), reverse=True)
    total = len(items)
    total_code = sum(1 for p in _papers if str(p.get("content.github_url","")).strip())
    if limit_p and limit_p.isdigit() and int(limit_p)>0:
        items = items[:int(limit_p)]
    return _json({"total": total, "total_with_code": total_code, "data": items})


@app.route("/api/jobs")
def jobs():
    query = request.args.get("search","").lower()
    role  = request.args.get("role","")
    items = list(_jobs)
    if role and role!="ALL":
        items = [j for j in items if role.lower() in str(j.get("content.role_family","")).lower()]
    if query:
        items = [j for j in items if
                 query in str(j.get("title","")).lower() or
                 query in str(j.get("content.company","")).lower()]
    return _json({"total": len(items), "data": items})


@app.route("/api/news")
def news():
    query  = request.args.get("search","").lower()
    source = request.args.get("source","")
    items  = list(_news)
    if source and source!="ALL":
        items = [n for n in items if source.lower() in str(n.get("source.name","")).lower()]
    if query:
        items = [n for n in items if query in str(n.get("content.title","")).lower()]
    return _json({"total": len(items), "data": items})


@app.route("/api/mappings")
def mappings():
    query   = request.args.get("search","").lower()
    limit_p = request.args.get("limit","")
    items   = list(_mappings)
    if query:
        items = [m for m in items if
                 query in str(m.get("raw_name","")).lower() or
                 query in str(m.get("canonical_name","")).lower()]
    total = len(items)
    if limit_p and limit_p.isdigit() and int(limit_p)>0:
        items = items[:int(limit_p)]
    return _json({"total": total, "data": items})


@app.route("/api/resolve", methods=["POST"])
def resolve():
    try:
        body     = request.get_json(force=True) or {}
        raw_name = (body.get("name") or "").strip()
        if not raw_name:
            return _json({"error": "Empty name provided"}, 400)
        # Simple fuzzy match without importing src.entity_resolution
        from rapidfuzz import process, fuzz
        names = [str(s.get("content.entityName","")) for s in _startups if s.get("content.entityName")]
        match = process.extractOne(raw_name, names, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= 80:
            return _json({"raw_name": raw_name, "canonical_name": match[0],
                          "confidence": round(match[1]/100, 3), "method": "fuzzy", "is_known": True})
        return _json({"raw_name": raw_name, "canonical_name": raw_name,
                      "confidence": 0.0, "method": "passthrough", "is_known": False})
    except Exception as e:
        return _json({"error": str(e)}, 500)


@app.route("/api/pipeline/status")
def pipeline_status():
    return _json({"sources": [], "recent_runs": [], "total_sources": 0,
                  "note": "Pipeline monitoring runs locally only."})


@app.route("/api/pipeline/logs")
def pipeline_logs():
    return _json({"runs": [], "note": "Pipeline logs available locally only."})


@app.route("/api/pipeline/run-now", methods=["POST"])
def pipeline_run_now():
    return _json({"status": "acknowledged",
                  "message": "Pipeline triggers not supported in serverless mode."})


@app.route("/api/trigger", methods=["POST"])
def trigger():
    return _json({"status": "acknowledged",
                  "message": "Pipeline triggers run locally only."})


@app.route("/api/download/xlsx")
def download_xlsx():
    path = DATA_DIR / "output_intelligence_graph.xlsx"
    if not path.exists():
        return _json({"error": "Excel not available"}, 404)
    return send_file(str(path), as_attachment=True,
                     download_name="GraphOne_Intelligence.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/api/download/pdf")
def download_pdf():
    path = PROJECT_ROOT / "architecture.pdf"
    if not path.exists():
        return _json({"error": "PDF not available"}, 404)
    return send_file(str(path), as_attachment=True,
                     download_name="GraphOne_Architecture.pdf",
                     mimetype="application/pdf")


@app.route("/api/graph/entities")
def graph_entities():
    cat_type = request.args.get("type","startups").lower().strip()
    result, seen = [], set()
    if cat_type in ("product","products"):
        for p in _products:
            name = str(p.get("product_name","")).strip()
            if name and name not in seen:
                seen.add(name)
                result.append({"name": name, "source": p.get("content.startupName") or "Product"})
    elif cat_type in ("paper","papers","research_papers"):
        for pa in _papers:
            title = str(pa.get("content.title","")).strip()
            if title and title not in seen:
                seen.add(title)
                result.append({"name": title, "source": f"{pa.get('content.github_stars',0)} Stars"})
    elif cat_type in ("job","jobs"):
        for j in _jobs:
            title = str(j.get("title","")).strip()
            if title and title not in seen:
                seen.add(title)
                result.append({"name": title, "source": j.get("content.company","Job")})
    elif cat_type in ("news","news_signals"):
        for n in _news:
            title = str(n.get("content.title","")).strip()
            if title and title not in seen:
                seen.add(title)
                result.append({"name": title, "source": n.get("source.name","News")})
    else:
        for s in _startups:
            name = str(s.get("content.entityName","")).strip()
            if name and name not in seen:
                seen.add(name)
                result.append({"name": name, "source": s.get("industry","Startup"), "is_seed": False})
        result.sort(key=lambda x: x["name"])
    return _json({"total": len(result), "entities": result[:300]})


@app.route("/api/graph/entity")
def graph_entity():
    raw_name    = request.args.get("name","").strip()
    entity_type = request.args.get("type","startups").lower().strip()
    if not raw_name:
        return _json({"error": "name parameter required"}, 400)

    # Find startup record
    startup_data = next(
        (s for s in _startups if str(s.get("content.entityName","")).lower()==raw_name.lower()), {}
    )
    if not startup_data:
        startup_data = next(
            (s for s in _startups if raw_name.lower() in str(s.get("content.entityName","")).lower()), {}
        )

    canonical   = str(startup_data.get("content.entityName", raw_name))
    startup_url = str(startup_data.get("content.data.website") or startup_data.get("source.url") or "").strip()
    sid         = "startup_center"
    nodes = [{"id": sid, "label": canonical, "group": "startup", "title": "",
               "url": startup_url or "/#startups", "value": 40, "shape": "ellipse",
               "color": {"background":"#6366F1","border":"#A5B4FC"},
               "font": {"color":"#FFFFFF","size":15,"face":"Inter"},
               "meta": {"type":"Startup","name":canonical,"url":startup_url}}]
    edges = []

    for i, p in enumerate([p for p in _products
                           if str(p.get("content.startupName","")).lower()==canonical.lower()][:4]):
        pid = f"prod_{i}"
        nodes.append({"id":pid,"label":str(p.get("product_name","")),"group":"product","title":"",
                      "url":str(p.get("source.url") or startup_url),"value":22,"shape":"dot",
                      "color":{"background":"#059669","border":"#34D399"},
                      "font":{"color":"#ECFDF5","size":11},"meta":{"type":"Product"}})
        edges.append({"from":sid,"to":pid,"label":"BUILDS","color":{"color":"#059669"},"length":150})

    for i, j in enumerate([j for j in _jobs
                           if canonical.lower() in str(j.get("content.company","")).lower()][:3]):
        jid = f"job_{i}"
        nodes.append({"id":jid,"label":str(j.get("title",""))[:24],"group":"job","title":"",
                      "url":str(j.get("job_url") or startup_url),"value":18,"shape":"dot",
                      "color":{"background":"#0284C7","border":"#7DD3FC"},
                      "font":{"color":"#F0F9FF","size":11},"meta":{"type":"Job"}})
        edges.append({"from":sid,"to":jid,"label":"HIRING","color":{"color":"#0284C7"},"length":170})

    for i, n in enumerate([n for n in _news
                           if canonical.lower() in str(n.get("content.title","")).lower()][:3]):
        nid = f"news_{i}"
        nodes.append({"id":nid,"label":str(n.get("content.title",""))[:25],"group":"news","title":"",
                      "url":str(n.get("source.url") or startup_url),"value":18,"shape":"dot",
                      "color":{"background":"#F43F5E","border":"#FECDD3"},
                      "font":{"color":"#FFF1F2","size":11},"meta":{"type":"News"}})
        edges.append({"from":sid,"to":nid,"label":"SIGNAL","color":{"color":"#F43F5E"},"length":200})

    return _json({"canonical_name":canonical,"entity_type":entity_type,
                  "startup":startup_data,"nodes":nodes,"edges":edges,
                  "counts":{"total_nodes":len(nodes),"total_edges":len(edges)}})
