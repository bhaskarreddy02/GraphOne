"""
GraphOne Intelligence Graph Web Application Server
Built with aiohttp.web. Serves API endpoints and interactive UI.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from aiohttp import web
import pandas as pd

from src.config import DATA_DIR
from src.entity_resolution.resolver import EntityResolver
from src.pipeline.runner import PipelineRunner

logger = logging.getLogger("WebServer")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = PROJECT_ROOT / "public"


class DataStore:
    def __init__(self):
        self.resolver = EntityResolver()
        self.reload_data()

    def reload_data(self):
        try:
            self.startups = pd.read_csv(DATA_DIR / "startups.csv").fillna("").to_dict(orient="records") if (DATA_DIR / "startups.csv").exists() else []
            self.products = pd.read_csv(DATA_DIR / "products.csv").fillna("").to_dict(orient="records") if (DATA_DIR / "products.csv").exists() else []
            self.papers = pd.read_csv(DATA_DIR / "research_papers.csv").fillna("").to_dict(orient="records") if (DATA_DIR / "research_papers.csv").exists() else []
            self.jobs = pd.read_csv(DATA_DIR / "jobs.csv").fillna("").to_dict(orient="records") if (DATA_DIR / "jobs.csv").exists() else []
            self.news = pd.read_csv(DATA_DIR / "news.csv").fillna("").to_dict(orient="records") if (DATA_DIR / "news.csv").exists() else []
            self.mappings = pd.read_csv(DATA_DIR / "entity_mapping_log.csv").fillna("").to_dict(orient="records") if (DATA_DIR / "entity_mapping_log.csv").exists() else []
        except Exception as e:
            logger.error(f"Error loading datasets: {e}")
            self.startups, self.products, self.papers, self.jobs, self.news, self.mappings = [], [], [], [], [], []


store = DataStore()


async def handle_stats(request: web.Request) -> web.Response:
    """Returns overview platform statistics."""
    stats = {
        "startups_count": len(store.startups),
        "products_count": len(store.products),
        "papers_count": len(store.papers),
        "jobs_count": len(store.jobs),
        "news_count": len(store.news),
        "mappings_count": len(store.mappings),
        "total_records": len(store.startups) + len(store.products) + len(store.papers) + len(store.jobs) + len(store.news),
        "avg_confidence": round(sum(float(m.get("confidence_score", 0.9)) for m in store.mappings) / max(1, len(store.mappings)), 3),
        "excel_available": (DATA_DIR / "output_intelligence_graph.xlsx").exists(),
        "pdf_available": (PROJECT_ROOT / "architecture.pdf").exists(),
    }
    return web.json_response(stats)


async def handle_startups(request: web.Request) -> web.Response:
    query = request.query.get("search", "").lower()
    industry = request.query.get("industry", "").strip().lower()
    team_size = request.query.get("team_size", "").strip()
    sort_by = request.query.get("sort_by", "").strip().lower()

    items = list(store.startups)

    # 1. Industry Category Filter
    if industry and industry != "all":
        items = [s for s in items if industry in str(s.get("industry", "")).lower()]

    # 2. Number of Employees / Team Size Filter
    if team_size and team_size != "all":
        def match_team_size(s, ts):
            raw = s.get("content.data.employeeCount")
            try:
                emp = float(raw) if raw not in (None, "") else -1
            except (ValueError, TypeError):
                emp = -1

            if ts == "1-5":
                return 1 <= emp <= 5
            elif ts == "6-15":
                return 6 <= emp <= 15
            elif ts == "16-50":
                return 16 <= emp <= 50
            elif ts == "50+":
                return emp > 50
            elif ts == "undisclosed":
                return emp <= 0
            return True

        items = [s for s in items if match_team_size(s, team_size)]

    # 3. Search query
    if query:
        items = [
            s for s in items
            if query in str(s.get("content.entityName", "")).lower()
            or query in str(s.get("industry", "")).lower()
            or query in str(s.get("description", "")).lower()
            or query in str(s.get("content.data.location", "")).lower()
        ]

    # 4. Sorting
    if sort_by == "team_desc":
        def get_emp(s):
            try:
                val = s.get("content.data.employeeCount")
                return float(val) if val not in (None, "") else -1
            except (ValueError, TypeError):
                return -1
        items.sort(key=get_emp, reverse=True)
    elif sort_by == "team_asc":
        def get_emp(s):
            try:
                val = s.get("content.data.employeeCount")
                return float(val) if val not in (None, "") else 999999
            except (ValueError, TypeError):
                return 999999
        items.sort(key=get_emp)
    elif sort_by == "name":
        items.sort(key=lambda s: str(s.get("content.entityName", "")).lower())

    limit = int(request.query.get("limit", "1000"))
    return web.json_response({"total": len(items), "data": items[:limit]})


async def handle_products(request: web.Request) -> web.Response:
    query = request.query.get("search", "").lower()
    pricing = request.query.get("pricing", "").upper()
    items = store.products
    if pricing and pricing != "ALL":
        items = [p for p in items if p.get("content.pricingModel") == pricing]
    if query:
        items = [p for p in items if query in str(p.get("product_name", "")).lower() or query in str(p.get("content.startupName", "")).lower()]
    limit = int(request.query.get("limit", "1000"))
    return web.json_response({"total": len(items), "data": items[:limit]})


async def handle_papers(request: web.Request) -> web.Response:
    query = request.query.get("search", "").lower()
    has_code = request.query.get("has_code", "").lower()
    source = request.query.get("source", "").strip()
    sort_by = request.query.get("sort_by", "impact").lower()

    items = list(store.papers)

    # 1. Filter by code repository availability
    if has_code == "true":
        items = [p for p in items if str(p.get("content.github_url", "")).strip()]
    elif has_code == "false":
        items = [p for p in items if not str(p.get("content.github_url", "")).strip()]

    # 2. Filter by source platform
    if source and source.upper() != "ALL":
        items = [p for p in items if source.lower() in str(p.get("content.source_platform", "")).lower()]

    # 3. Search query
    if query:
        items = [
            p for p in items
            if query in str(p.get("content.title", "")).lower()
            or query in str(p.get("content.authors", "")).lower()
            or query in str(p.get("content.github_url", "")).lower()
        ]

    # 4. Sorting & Ranking
    def get_num(val, default=0):
        try:
            return float(val) if val is not None and str(val).strip() != "" else default
        except (ValueError, TypeError):
            return default

    if sort_by == "stars":
        items.sort(key=lambda p: get_num(p.get("content.github_stars", 0)), reverse=True)
    elif sort_by == "upvotes":
        items.sort(key=lambda p: get_num(p.get("content.huggingface_upvotes", 0)), reverse=True)
    elif sort_by == "date":
        items.sort(key=lambda p: str(p.get("content.published_date", "")), reverse=True)
    else:  # impact / default
        items.sort(
            key=lambda p: (
                1 if str(p.get("content.github_url", "")).strip() else 0,
                get_num(p.get("content.impact_score", 0)),
                get_num(p.get("content.github_stars", 0)),
                get_num(p.get("content.huggingface_upvotes", 0)),
                str(p.get("content.published_date", ""))
            ),
            reverse=True
        )

    limit = int(request.query.get("limit", "1000"))
    return web.json_response({
        "total": len(items),
        "total_with_code": sum(1 for p in store.papers if str(p.get("content.github_url", "")).strip()),
        "data": items[:limit]
    })


async def handle_jobs(request: web.Request) -> web.Response:
    query = request.query.get("search", "").lower()
    role = request.query.get("role", "")
    items = store.jobs
    if role and role != "ALL":
        items = [j for j in items if role.lower() in str(j.get("content.role_family", "")).lower()]
    if query:
        items = [j for j in items if query in str(j.get("title", "")).lower() or query in str(j.get("content.company", "")).lower()]
    return web.json_response({"total": len(items), "data": items})


async def handle_news(request: web.Request) -> web.Response:
    query = request.query.get("search", "").lower()
    source = request.query.get("source", "")
    items = store.news
    if source and source != "ALL":
        items = [n for n in items if source.lower() in str(n.get("source.name", "")).lower()]
    if query:
        items = [n for n in items if query in str(n.get("content.title", "")).lower()]
    return web.json_response({"total": len(items), "data": items})


async def handle_mappings(request: web.Request) -> web.Response:
    query = request.query.get("search", "").lower()
    items = store.mappings
    if query:
        items = [m for m in items if query in str(m.get("raw_name", "")).lower() or query in str(m.get("canonical_name", "")).lower()]
    limit = int(request.query.get("limit", "500"))
    return web.json_response({"total": len(items), "data": items[:limit]})


async def handle_resolve_live(request: web.Request) -> web.Response:
    """Real-time deterministic entity resolution API for interactive testing."""
    try:
        body = await request.json()
        raw_name = body.get("name", "")
        canonical, confidence, method = store.resolver.resolve(raw_name, source_context="UI Interactive Tester")
        return web.json_response({
            "raw_name": raw_name,
            "canonical_name": canonical,
            "confidence_score": confidence,
            "resolution_method": method
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def handle_download_excel(request: web.Request) -> web.FileResponse:
    excel_path = DATA_DIR / "output_intelligence_graph.xlsx"
    if not excel_path.exists():
        raise web.HTTPNotFound(text="Excel workbook not generated yet.")
    return web.FileResponse(excel_path, headers={"Content-Disposition": 'attachment; filename="GraphOne_Intelligence_Graph.xlsx"'})


async def handle_download_pdf(request: web.Request) -> web.FileResponse:
    pdf_path = PROJECT_ROOT / "architecture.pdf"
    if not pdf_path.exists():
        raise web.HTTPNotFound(text="Architecture PDF not generated yet.")
    return web.FileResponse(pdf_path, headers={"Content-Disposition": 'attachment; filename="GraphOne_Architecture.pdf"'})


async def handle_pipeline_status(request: web.Request) -> web.Response:
    """Returns persistent state of all sources and recent monitoring cycles."""
    from src.pipeline.state_store import PipelineStateStore
    state_store = PipelineStateStore()
    sources = state_store.get_all_source_states()
    recent_runs = state_store.get_recent_runs(limit=10)
    return web.json_response({
        "sources": sources,
        "recent_runs": recent_runs,
        "total_sources": len(sources)
    })


async def handle_pipeline_logs(request: web.Request) -> web.Response:
    """Returns crawl run audit logs."""
    from src.pipeline.state_store import PipelineStateStore
    state_store = PipelineStateStore()
    runs = state_store.get_recent_runs(limit=25)
    return web.json_response({"runs": runs})


async def handle_pipeline_run_now(request: web.Request) -> web.Response:
    """Triggers an immediate cycle across all 10 sources."""
    async def _run_cycle_bg():
        from src.pipeline.monitor import ContinuousMonitoringPipeline
        pipeline = ContinuousMonitoringPipeline()
        await pipeline.run_cycle()
        store.reload_data()

    asyncio.create_task(_run_cycle_bg())
    return web.json_response({
        "status": "triggered",
        "message": "Continuous monitoring cycle initiated across all 10 sources in background"
    })


async def handle_trigger_pipeline(request: web.Request) -> web.Response:
    """Triggers an async pipeline reload/run in background."""
    asyncio.create_task(_run_pipeline_background())
    return web.json_response({"status": "started", "message": "Pipeline run triggered concurrently"})


async def _run_pipeline_background():
    runner = PipelineRunner(target_startups=1000, target_products=1000, target_papers=1000)
    await runner.run()
    store.reload_data()


def create_app() -> web.Application:
    app = web.Application()
    # API routes
    app.router.add_get("/api/stats", handle_stats)
    app.router.add_get("/api/startups", handle_startups)
    app.router.add_get("/api/products", handle_products)
    app.router.add_get("/api/papers", handle_papers)
    app.router.add_get("/api/jobs", handle_jobs)
    app.router.add_get("/api/news", handle_news)
    app.router.add_get("/api/mappings", handle_mappings)
    app.router.add_post("/api/resolve", handle_resolve_live)
    app.router.add_get("/api/download/xlsx", handle_download_excel)
    app.router.add_get("/api/download/pdf", handle_download_pdf)
    app.router.add_post("/api/trigger", handle_trigger_pipeline)

    # Phase 2 Monitoring Pipeline routes
    app.router.add_get("/api/pipeline/status", handle_pipeline_status)
    app.router.add_get("/api/pipeline/logs", handle_pipeline_logs)
    app.router.add_post("/api/pipeline/run-now", handle_pipeline_run_now)


    # Static assets
    PUBLIC_DIR.mkdir(exist_ok=True, parents=True)
    app.router.add_static("/static/", path=PUBLIC_DIR, name="static")

    async def index_handler(request):
        return web.FileResponse(PUBLIC_DIR / "index.html")

    async def activity_handler(request):
        return web.FileResponse(PUBLIC_DIR / "activity.html")

    app.router.add_get("/", index_handler)
    app.router.add_get("/activity", activity_handler)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8000)
