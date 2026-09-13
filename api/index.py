"""
Vercel WSGI entry point for GraphOne — Flask implementation.
Flask is natively supported by Vercel's @vercel/python runtime (WSGI).
This mirrors all API routes from src/server.py without requiring aiohttp.
"""

import sys
import json
import logging
from pathlib import Path

# Ensure project root is on sys.path so src.* imports resolve
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, jsonify, send_file, Response
import pandas as pd

logger = logging.getLogger("VercelAPI")

# ---------------------------------------------------------------------------
# Data store — loaded once per cold start
# ---------------------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"

def _load_csv(name):
    path = DATA_DIR / name
    if path.exists():
        try:
            return pd.read_csv(path).fillna("").to_dict(orient="records")
        except Exception as e:
            logger.error(f"Error loading {name}: {e}")
    return []

startups  = _load_csv("startups.csv")
products  = _load_csv("products.csv")
papers    = _load_csv("research_papers.csv")
jobs      = _load_csv("jobs.csv")
news      = _load_csv("news.csv")
mappings  = _load_csv("entity_mapping_log.csv")

# Lazy-load entity resolver (heavy import)
_resolver = None
def get_resolver():
    global _resolver
    if _resolver is None:
        try:
            from src.entity_resolution.resolver import EntityResolver
            _resolver = EntityResolver()
        except Exception as e:
            logger.error(f"Resolver init failed: {e}")
    return _resolver

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)

def _json(data, status=200):
    return Response(json.dumps(data, ensure_ascii=False, default=str),
                    status=status, mimetype="application/json")

# Helper: safe numeric
def _num(val, default=0):
    try:
        return float(val) if val is not None and str(val).strip() != "" else default
    except (ValueError, TypeError):
        return default


# ------------------------------------------------------------------
# GET /api/stats
# ------------------------------------------------------------------
@app.route("/api/stats")
def api_stats():
    avg_conf = round(
        sum(float(m.get("confidence_score", 0.9)) for m in mappings) / max(1, len(mappings)), 3
    )
    return _json({
        "startups_count": len(startups),
        "products_count": len(products),
        "papers_count":   len(papers),
        "jobs_count":     len(jobs),
        "news_count":     len(news),
        "mappings_count": len(mappings),
        "total_records":  len(startups) + len(products) + len(papers) + len(jobs) + len(news),
        "avg_confidence": avg_conf,
        "excel_available": (DATA_DIR / "output_intelligence_graph.xlsx").exists(),
        "pdf_available":   (PROJECT_ROOT / "architecture.pdf").exists(),
    })


# ------------------------------------------------------------------
# GET /api/startups
# ------------------------------------------------------------------
@app.route("/api/startups")
def api_startups():
    query     = request.args.get("search", "").lower()
    industry  = request.args.get("industry", "").strip().lower()
    team_size = request.args.get("team_size", "").strip()
    sort_by   = request.args.get("sort_by", "").strip().lower()
    limit_p   = request.args.get("limit", "")

    items = list(startups)

    if industry and industry != "all":
        items = [s for s in items if industry in str(s.get("industry", "")).lower()]

    if team_size and team_size != "all":
        def _match_ts(s, ts):
            raw = s.get("content.data.employeeCount")
            try:
                emp = float(raw) if raw not in (None, "") else -1
            except (ValueError, TypeError):
                emp = -1
            if ts == "1-5":    return 1  <= emp <= 5
            if ts == "6-15":   return 6  <= emp <= 15
            if ts == "16-50":  return 16 <= emp <= 50
            if ts == "50+":    return emp > 50
            if ts == "undisclosed": return emp <= 0
            return True
        items = [s for s in items if _match_ts(s, team_size)]

    if query:
        items = [s for s in items
                 if query in str(s.get("content.entityName", "")).lower()
                 or query in str(s.get("industry", "")).lower()
                 or query in str(s.get("description", "")).lower()
                 or query in str(s.get("content.data.location", "")).lower()]

    if sort_by == "team_desc":
        items.sort(key=lambda s: _num(s.get("content.data.employeeCount"), -1), reverse=True)
    elif sort_by == "team_asc":
        items.sort(key=lambda s: _num(s.get("content.data.employeeCount"), 999999))
    elif sort_by == "name":
        items.sort(key=lambda s: str(s.get("content.entityName", "")).lower())

    total = len(items)
    if limit_p and limit_p.isdigit() and int(limit_p) > 0:
        items = items[:int(limit_p)]
    return _json({"total": total, "data": items})


# ------------------------------------------------------------------
# GET /api/products
# ------------------------------------------------------------------
@app.route("/api/products")
def api_products():
    query   = request.args.get("search", "").lower()
    pricing = request.args.get("pricing", "").upper()
    limit_p = request.args.get("limit", "")
    items   = list(products)
    if pricing and pricing != "ALL":
        items = [p for p in items if p.get("content.pricingModel") == pricing]
    if query:
        items = [p for p in items
                 if query in str(p.get("product_name", "")).lower()
                 or query in str(p.get("content.startupName", "")).lower()]
    total = len(items)
    if limit_p and limit_p.isdigit() and int(limit_p) > 0:
        items = items[:int(limit_p)]
    return _json({"total": total, "data": items})


# ------------------------------------------------------------------
# GET /api/papers
# ------------------------------------------------------------------
@app.route("/api/papers")
def api_papers():
    query    = request.args.get("search", "").lower()
    has_code = request.args.get("has_code", "").lower()
    source   = request.args.get("source", "").strip()
    sort_by  = request.args.get("sort_by", "impact").lower()
    limit_p  = request.args.get("limit", "")
    items    = list(papers)

    if has_code == "true":
        items = [p for p in items if str(p.get("content.github_url", "")).strip()]
    elif has_code == "false":
        items = [p for p in items if not str(p.get("content.github_url", "")).strip()]

    if source and source.upper() != "ALL":
        items = [p for p in items
                 if source.lower() in str(p.get("content.source_platform", "")).lower()]

    if query:
        items = [p for p in items
                 if query in str(p.get("content.title", "")).lower()
                 or query in str(p.get("content.authors", "")).lower()
                 or query in str(p.get("content.abstract", "")).lower()]

    if sort_by == "stars":
        items.sort(key=lambda p: _num(p.get("content.github_stars", 0)), reverse=True)
    elif sort_by == "upvotes":
        items.sort(key=lambda p: _num(p.get("content.huggingface_upvotes", 0)), reverse=True)
    elif sort_by == "date":
        items.sort(key=lambda p: str(p.get("content.published_date", "")), reverse=True)
    else:
        items.sort(key=lambda p: (
            1 if str(p.get("content.github_url", "")).strip() else 0,
            _num(p.get("content.impact_score", 0)),
            _num(p.get("content.github_stars", 0)),
            _num(p.get("content.huggingface_upvotes", 0)),
            str(p.get("content.published_date", ""))
        ), reverse=True)

    total = len(items)
    total_code = sum(1 for p in papers if str(p.get("content.github_url", "")).strip())
    if limit_p and limit_p.isdigit() and int(limit_p) > 0:
        items = items[:int(limit_p)]
    return _json({"total": total, "total_with_code": total_code, "data": items})


# ------------------------------------------------------------------
# GET /api/jobs
# ------------------------------------------------------------------
@app.route("/api/jobs")
def api_jobs():
    query   = request.args.get("search", "").lower()
    role    = request.args.get("role", "")
    items   = list(jobs)
    if role and role != "ALL":
        items = [j for j in items
                 if role.lower() in str(j.get("content.role_family", "")).lower()]
    if query:
        items = [j for j in items
                 if query in str(j.get("title", "")).lower()
                 or query in str(j.get("content.company", "")).lower()]
    return _json({"total": len(items), "data": items})


# ------------------------------------------------------------------
# GET /api/news
# ------------------------------------------------------------------
@app.route("/api/news")
def api_news():
    query  = request.args.get("search", "").lower()
    source = request.args.get("source", "")
    items  = list(news)
    if source and source != "ALL":
        items = [n for n in items
                 if source.lower() in str(n.get("source.name", "")).lower()]
    if query:
        items = [n for n in items
                 if query in str(n.get("content.title", "")).lower()]
    return _json({"total": len(items), "data": items})


# ------------------------------------------------------------------
# GET /api/mappings
# ------------------------------------------------------------------
@app.route("/api/mappings")
def api_mappings():
    query   = request.args.get("search", "").lower()
    limit_p = request.args.get("limit", "")
    items   = list(mappings)
    if query:
        items = [m for m in items
                 if query in str(m.get("raw_name", "")).lower()
                 or query in str(m.get("canonical_name", "")).lower()]
    total = len(items)
    if limit_p and limit_p.isdigit() and int(limit_p) > 0:
        items = items[:int(limit_p)]
    return _json({"total": total, "data": items})


# ------------------------------------------------------------------
# POST /api/resolve
# ------------------------------------------------------------------
@app.route("/api/resolve", methods=["POST"])
def api_resolve():
    try:
        body = request.get_json(force=True) or {}
        raw_name = (body.get("name") or "").strip()
        if not raw_name:
            return _json({"error": "Empty name provided"}, 400)
        resolver = get_resolver()
        if resolver is None:
            return _json({"error": "Resolver unavailable"}, 503)
        decision = resolver.resolve_entity(raw_name, return_details=True)
        return _json({
            "raw_name":       decision["raw_name"],
            "canonical_name": decision["canonical_name"],
            "confidence":     decision.get("confidence", 0),
            "method":         decision.get("method", "unknown"),
            "match_score":    decision.get("match_score", 0),
            "is_known":       decision.get("is_known", False),
        })
    except Exception as e:
        return _json({"error": str(e)}, 500)


# ------------------------------------------------------------------
# GET /api/pipeline/status
# ------------------------------------------------------------------
@app.route("/api/pipeline/status")
def api_pipeline_status():
    try:
        from src.pipeline.state_store import PipelineStateStore
        ss = PipelineStateStore()
        sources = ss.get_all_source_states()
        runs    = ss.get_recent_runs(limit=10)
        return _json({"sources": sources, "recent_runs": runs, "total_sources": len(sources)})
    except Exception as e:
        return _json({"sources": [], "recent_runs": [], "total_sources": 0, "error": str(e)})


# ------------------------------------------------------------------
# GET /api/pipeline/logs
# ------------------------------------------------------------------
@app.route("/api/pipeline/logs")
def api_pipeline_logs():
    try:
        from src.pipeline.state_store import PipelineStateStore
        ss = PipelineStateStore()
        runs = ss.get_recent_runs(limit=25)
        return _json({"runs": runs})
    except Exception as e:
        return _json({"runs": [], "error": str(e)})


# ------------------------------------------------------------------
# POST /api/pipeline/run-now  (no-op on serverless — just ack)
# ------------------------------------------------------------------
@app.route("/api/pipeline/run-now", methods=["POST"])
def api_pipeline_run_now():
    return _json({
        "status": "acknowledged",
        "message": "Pipeline triggers are not supported in serverless mode. Run locally."
    })


# ------------------------------------------------------------------
# POST /api/trigger  (legacy compat)
# ------------------------------------------------------------------
@app.route("/api/trigger", methods=["POST"])
def api_trigger():
    return _json({"status": "acknowledged",
                  "message": "Pipeline triggers run locally only."})


# ------------------------------------------------------------------
# GET /api/download/xlsx
# ------------------------------------------------------------------
@app.route("/api/download/xlsx")
def api_download_xlsx():
    path = DATA_DIR / "output_intelligence_graph.xlsx"
    if not path.exists():
        return _json({"error": "Excel file not available"}, 404)
    return send_file(str(path), as_attachment=True,
                     download_name="GraphOne_Intelligence.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ------------------------------------------------------------------
# GET /api/download/pdf
# ------------------------------------------------------------------
@app.route("/api/download/pdf")
def api_download_pdf():
    path = PROJECT_ROOT / "architecture.pdf"
    if not path.exists():
        return _json({"error": "PDF not available"}, 404)
    return send_file(str(path), as_attachment=True,
                     download_name="GraphOne_Architecture.pdf",
                     mimetype="application/pdf")


# ------------------------------------------------------------------
# GET /api/graph/entities
# ------------------------------------------------------------------
@app.route("/api/graph/entities")
def api_graph_entities():
    try:
        from src.entity_resolution.seed_database import SEED_CANONICAL_STARTUPS
    except Exception:
        SEED_CANONICAL_STARTUPS = {}

    cat_type = request.args.get("type", "startups").lower().strip()
    result = []
    seen   = set()

    if cat_type in ("product", "products"):
        for p in products:
            name = str(p.get("product_name", "")).strip()
            if name and name not in seen:
                seen.add(name)
                result.append({"name": name, "source": p.get("content.startupName") or p.get("category", "Product")})
    elif cat_type in ("paper", "papers", "research_papers"):
        for pa in papers:
            title = str(pa.get("content.title", "")).strip()
            if title and title not in seen:
                seen.add(title)
                result.append({"name": title, "source": f"{pa.get('content.github_stars', 0)} Stars"})
    elif cat_type in ("job", "jobs"):
        for j in jobs:
            title = str(j.get("title", "")).strip()
            if title and title not in seen:
                seen.add(title)
                result.append({"name": title, "source": j.get("content.company", "Job Opening")})
    elif cat_type in ("news", "news_signals"):
        for n in news:
            title = str(n.get("content.title", "")).strip()
            if title and title not in seen:
                seen.add(title)
                result.append({"name": title, "source": n.get("source.name", "News Signal")})
    else:
        for k in SEED_CANONICAL_STARTUPS.keys():
            if k not in seen:
                seen.add(k)
                result.append({"name": k, "source": "Frontier AI", "is_seed": True})
        for s in startups:
            name = str(s.get("content.entityName", "")).strip()
            if name and name not in seen:
                seen.add(name)
                result.append({"name": name, "source": s.get("industry", "YC Startup"), "is_seed": False})
        result.sort(key=lambda x: (not x.get("is_seed", False), x["name"]))
        return _json({"total": len(result), "entities": result})

    return _json({"total": len(result), "entities": result[:200]})


# ------------------------------------------------------------------
# GET /api/graph/entity  — full graph data for one entity
# (minimal version: returns startup + connected nodes)
# ------------------------------------------------------------------
@app.route("/api/graph/entity")
def api_graph_entity():
    try:
        from src.entity_resolution.seed_database import SEED_CANONICAL_STARTUPS
    except Exception:
        SEED_CANONICAL_STARTUPS = {}

    raw_name    = request.args.get("name", "").strip()
    entity_type = request.args.get("type", "startups").lower().strip()
    if not raw_name:
        return _json({"error": "Query parameter 'name' is required"}, 400)

    # Delegate to the resolver for canonical name
    resolver = get_resolver()
    canonical = raw_name
    startup_data = {}
    if resolver:
        try:
            decision  = resolver.resolve_entity(raw_name, return_details=True)
            canonical = decision.get("canonical_name", raw_name)
        except Exception:
            pass

    # Find startup record
    startup_record = next(
        (s for s in startups if str(s.get("content.entityName", "")).lower() == canonical.lower()), None
    )
    if not startup_record:
        startup_record = next(
            (s for s in startups if canonical.lower() in str(s.get("content.entityName", "")).lower()), None
        )
    if startup_record:
        startup_data = startup_record

    nodes, edges = [], []
    startup_url = str(startup_data.get("content.data.website") or startup_data.get("source.url") or "").strip()
    startup_id  = "startup_center"

    nodes.append({
        "id": startup_id,
        "label": canonical,
        "group": "startup",
        "title": "",
        "url": startup_url or "/#startups",
        "value": 40,
        "shape": "ellipse",
        "color": {"background": "#6366F1", "border": "#A5B4FC",
                  "highlight": {"background": "#4F46E5", "border": "#FFFFFF"}},
        "font": {"color": "#FFFFFF", "size": 15, "face": "Inter", "bold": "true"},
        "meta": {"type": "Startup", "name": canonical,
                 "description": startup_data.get("description", ""),
                 "url": startup_url}
    })

    # Related products
    matched_prods = [p for p in products
                     if str(p.get("content.startupName", "")).lower() == canonical.lower()][:4]
    prod_node_ids = []
    for i, p in enumerate(matched_prods):
        pid = f"prod_{i}"
        prod_node_ids.append(pid)
        p_name = str(p.get("product_name", "Product"))
        p_url  = str(p.get("source.url") or "").strip()
        nodes.append({"id": pid, "label": p_name, "group": "product", "title": "",
                      "url": p_url or startup_url, "value": 22, "shape": "dot",
                      "color": {"background": "#059669", "border": "#34D399"},
                      "font": {"color": "#ECFDF5", "size": 11, "face": "Inter"},
                      "meta": {"type": "Product", "name": p_name, "url": p_url}})
        edges.append({"from": startup_id, "to": pid, "label": "BUILDS",
                      "color": {"color": "#059669"}, "length": 150})

    # Related papers
    matched_papers = [pa for pa in papers
                      if canonical.lower() in str(pa.get("content.title", "")).lower()
                      or canonical.lower() in str(pa.get("content.authors", "")).lower()][:3]
    for i, pa in enumerate(matched_papers):
        paid = f"paper_{i}"
        title = str(pa.get("content.title", "Research Paper"))[:40]
        pa_url = str(pa.get("content.arxiv_url") or pa.get("content.github_url") or "").strip()
        nodes.append({"id": paid, "label": title, "group": "paper", "title": "",
                      "url": pa_url or startup_url, "value": 18, "shape": "dot",
                      "color": {"background": "#D97706", "border": "#FDE68A"},
                      "font": {"color": "#FFFBEB", "size": 11, "face": "Inter"},
                      "meta": {"type": "Research Paper", "title": title, "url": pa_url}})
        edges.append({"from": startup_id, "to": paid, "label": "RESEARCH",
                      "color": {"color": "#F59E0B"}, "length": 180})

    # Related jobs
    matched_jobs = [j for j in jobs
                    if canonical.lower() in str(j.get("content.company", "")).lower()
                    or canonical.lower() in str(j.get("title", "")).lower()][:3]
    for i, j in enumerate(matched_jobs):
        jid = f"job_{i}"
        j_title = str(j.get("title", "Job Role"))
        j_url   = str(j.get("job_url") or startup_url).strip()
        nodes.append({"id": jid, "label": j_title[:24], "group": "job", "title": "",
                      "url": j_url or startup_url, "value": 18, "shape": "dot",
                      "color": {"background": "#0284C7", "border": "#7DD3FC"},
                      "font": {"color": "#F0F9FF", "size": 11, "face": "Inter"},
                      "meta": {"type": "Job Opening", "title": j_title, "url": j_url}})
        edges.append({"from": startup_id, "to": jid, "label": "HIRING",
                      "color": {"color": "#0284C7"}, "length": 170})

    # Related news
    matched_news = [n for n in news
                    if canonical.lower() in str(n.get("content.title", "")).lower()][:3]
    for i, n in enumerate(matched_news):
        nid = f"news_{i}"
        n_title = str(n.get("content.title", "News Signal"))
        n_url   = str(n.get("source.url") or "").strip()
        nodes.append({"id": nid, "label": n_title[:25], "group": "news", "title": "",
                      "url": n_url or startup_url, "value": 18, "shape": "dot",
                      "color": {"background": "#F43F5E", "border": "#FECDD3"},
                      "font": {"color": "#FFF1F2", "size": 11, "face": "Inter"},
                      "meta": {"type": "News Signal", "title": n_title, "url": n_url}})
        edges.append({"from": startup_id, "to": nid, "label": "SIGNAL",
                      "color": {"color": "#F43F5E"}, "length": 200})

    return _json({
        "canonical_name": canonical,
        "entity_type":    entity_type,
        "startup":        startup_data,
        "nodes":          nodes,
        "edges":          edges,
        "counts": {
            "products": len(matched_prods),
            "papers":   len(matched_papers),
            "jobs":     len(matched_jobs),
            "news":     len(matched_news),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }
    })


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@app.route("/api/health")
def api_health():
    return _json({
        "status": "ok",
        "records": {
            "startups": len(startups),
            "products": len(products),
            "papers":   len(papers),
            "jobs":     len(jobs),
            "news":     len(news),
        }
    })
