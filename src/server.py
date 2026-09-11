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
    items = store.startups
    if query:
        items = [s for s in items if query in str(s.get("content.entityName", "")).lower() or query in str(s.get("industry", "")).lower()]
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
    has_github = request.query.get("has_github", "").lower() == "true"
    items = store.papers
    if has_github:
        items = [p for p in items if p.get("content.github_url")]
    if query:
        items = [p for p in items if query in str(p.get("content.title", "")).lower() or query in str(p.get("content.authors", "")).lower()]
    limit = int(request.query.get("limit", "1000"))
    return web.json_response({"total": len(items), "data": items[:limit]})


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

    # Static assets
    PUBLIC_DIR.mkdir(exist_ok=True, parents=True)
    app.router.add_static("/static/", path=PUBLIC_DIR, name="static")

    async def index_handler(request):
        return web.FileResponse(PUBLIC_DIR / "index.html")

    app.router.add_get("/", index_handler)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8000)
