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

    limit_param = request.query.get("limit")
    if limit_param and limit_param.isdigit() and int(limit_param) > 0:
        return web.json_response({"total": len(items), "data": items[:int(limit_param)]})
    return web.json_response({"total": len(items), "data": items})


async def handle_products(request: web.Request) -> web.Response:
    query = request.query.get("search", "").lower()
    pricing = request.query.get("pricing", "").upper()
    items = store.products
    if pricing and pricing != "ALL":
        items = [p for p in items if p.get("content.pricingModel") == pricing]
    if query:
        items = [p for p in items if query in str(p.get("product_name", "")).lower() or query in str(p.get("content.startupName", "")).lower()]
    limit_param = request.query.get("limit")
    if limit_param and limit_param.isdigit() and int(limit_param) > 0:
        return web.json_response({"total": len(items), "data": items[:int(limit_param)]})
    return web.json_response({"total": len(items), "data": items})


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
            or query in str(p.get("content.abstract", "")).lower()
        ]

    # 4. Sorting logic
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

    limit_param = request.query.get("limit")
    sliced = items[:int(limit_param)] if (limit_param and limit_param.isdigit() and int(limit_param) > 0) else items
    return web.json_response({
        "total": len(items),
        "total_with_code": sum(1 for p in store.papers if str(p.get("content.github_url", "")).strip()),
        "data": sliced
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
    limit_param = request.query.get("limit")
    sliced = items[:int(limit_param)] if (limit_param and limit_param.isdigit() and int(limit_param) > 0) else items
    return web.json_response({"total": len(items), "data": sliced})


async def handle_resolve_live(request: web.Request) -> web.Response:
    """Deterministic entity resolution: Exact normalized lookup + RapidFuzz similarity matching."""
    try:
        body = await request.json()
        raw_name = (body.get("name") or "").strip()
        if not raw_name:
            return web.json_response({"error": "Empty name provided"}, status=400)

        decision = store.resolver.resolve_entity(raw_name, return_details=True)
        return web.json_response({
            "raw_name": decision["raw_name"],
            "canonical_name": decision["canonical_name"],
            "confidence_score": decision["confidence"],
            "resolution_method": decision["method"],
            "decision": decision,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


async def handle_download_excel(request: web.Request) -> web.FileResponse:
    excel_path = DATA_DIR / "output_intelligence_graph.xlsx"
    if not excel_path.exists():
        raise web.HTTPNotFound(text="Excel workbook not generated yet.")
    return web.FileResponse(
        excel_path,
        headers={
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "Content-Disposition": 'attachment; filename="GraphOne_Intelligence_Graph.xlsx"',
            "Cache-Control": "no-cache"
        }
    )


async def handle_download_pdf(request: web.Request) -> web.FileResponse:
    pdf_path = PROJECT_ROOT / "architecture.pdf"
    if not pdf_path.exists():
        raise web.HTTPNotFound(text="Architecture PDF not generated yet.")
    return web.FileResponse(
        pdf_path,
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="GraphOne_Architecture.pdf"',
            "Cache-Control": "no-cache"
        }
    )


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


async def handle_graph_entity(request: web.Request) -> web.Response:
    """Returns dynamic knowledge graph node-link data for any selected entity across Startups, Products, Papers, Jobs, or News."""
    from src.entity_resolution.seed_database import SEED_CANONICAL_STARTUPS
    raw_name = request.query.get("name", "").strip()
    entity_type = request.query.get("type", "startups").lower().strip()
    if not raw_name:
        return web.json_response({"error": "Query parameter 'name' is required"}, status=400)

    # Normalize entity_type
    if entity_type in ("startup", "startups"):
        entity_type = "startups"
    elif entity_type in ("product", "products"):
        entity_type = "products"
    elif entity_type in ("paper", "papers", "research_papers"):
        entity_type = "papers"
    elif entity_type in ("job", "jobs"):
        entity_type = "jobs"
    elif entity_type in ("news", "news_signals"):
        entity_type = "news"

    nodes = []
    edges = []

    # =========================================================
    # 1. PRODUCT CENTRIC GRAPH
    # =========================================================
    if entity_type == "products":
        # Find product
        prod = next((p for p in store.products if raw_name.lower() == str(p.get("product_name", "")).lower()), None)
        if not prod:
            prod = next((p for p in store.products if raw_name.lower() in str(p.get("product_name", "")).lower()), None)
        if not prod:
            prod = {
                "product_name": raw_name,
                "content.startupName": "AI Ecosystem",
                "content.pricingModel": "Freemium",
                "category": "AI Solution",
                "source.url": "",
                "description": f"AI product: {raw_name}."
            }

        prod_name = prod.get("product_name")
        prod_url = str(prod.get("source.url") or "").strip()
        pricing = str(prod.get("content.pricingModel", "Freemium"))
        category = str(prod.get("category", "AI Tool"))
        creator = str(prod.get("content.startupName", "")).strip()

        # Central Product Node (Oval shape)
        center_id = f"prod_{prod_name.replace(' ', '_')}"
        nodes.append({
            "id": center_id,
            "label": f"🚀 {prod_name}",
            "group": "product",
            "title": "",
            "url": prod_url or "/#products",
            "value": 38,
            "shape": "ellipse",
            "margin": 14,
            "borderWidth": 2.5,
            "shadow": { "enabled": True, "color": "rgba(16, 185, 129, 0.45)", "size": 16, "x": 0, "y": 4 },
            "color": {
                "background": "#059669",
                "border": "#A7F3D0",
                "highlight": { "background": "#047857", "border": "#FFFFFF" }
            },
            "font": { "color": "#FFFFFF", "size": 14, "face": "Inter", "bold": "true" },
            "meta": {
                "type": "Product",
                "name": prod_name,
                "creator": creator,
                "pricing": pricing,
                "category": category,
                "description": prod.get("description", ""),
                "url": prod_url
            }
        })

        # Creator / Parent Startup Node
        if creator and creator.lower() != "unknown":
            st_data = next((s for s in store.startups if str(s.get("content.entityName", "")).lower() == creator.lower()), None)
            if not st_data and creator in SEED_CANONICAL_STARTUPS:
                seed = SEED_CANONICAL_STARTUPS[creator]
                st_data = {
                    "content.entityName": creator,
                    "content.data.website": f"https://{seed.get('domain', '')}",
                    "industry": "Artificial Intelligence",
                    "description": f"Frontier AI organization ({creator})."
                }
            st_url = str(st_data.get("content.data.website") or st_data.get("source.url") or "") if st_data else ""
            st_id = f"startup_{creator.replace(' ', '_')}"
            nodes.append({
                "id": st_id,
                "label": f"🏢 {creator}",
                "group": "startup",
                "title": "",
                "url": st_url or "/#startups",
                "value": 30,
                "shape": "dot",
                "color": { "background": "#6366F1", "border": "#A5B4FC" },
                "font": { "color": "#FFFFFF", "size": 13, "face": "Inter" },
                "meta": { "type": "Startup", "name": creator, "url": st_url, "description": st_data.get("description", "") if st_data else "" }
            })
            edges.append({ "from": center_id, "to": st_id, "label": "BUILT_BY", "color": { "color": "#6366F1" }, "length": 140 })

            # Sibling Products by same creator (interconnected to startup)
            siblings = [p for p in store.products if str(p.get("content.startupName", "")).lower() == creator.lower() and str(p.get("product_name", "")).lower() != prod_name.lower()][:3]
            for i, sib in enumerate(siblings):
                sib_id = f"sib_prod_{i}"
                sib_name = sib.get("product_name")
                nodes.append({
                    "id": sib_id,
                    "label": f"🚀 {sib_name}",
                    "group": "product",
                    "title": "",
                    "url": sib.get("source.url") or st_url,
                    "value": 20,
                    "shape": "dot",
                    "color": { "background": "#059669", "border": "#34D399" },
                    "font": { "color": "#ECFDF5", "size": 11 },
                    "meta": { "type": "Product", "name": sib_name, "creator": creator, "pricing": sib.get("content.pricingModel"), "url": sib.get("source.url") }
                })
                edges.append({ "from": st_id, "to": sib_id, "label": "ALSO_BUILDS", "color": { "color": "#10B981" }, "length": 190 })

        # Category & Pricing Nodes
        cat_id = f"cat_{center_id}"
        nodes.append({
            "id": cat_id,
            "label": category,
            "group": "category",
            "title": "",
            "url": "/#products",
            "value": 16,
            "shape": "box",
            "color": { "background": "#1E293B", "border": "#475569" },
            "font": { "color": "#E2E8F0", "size": 11 },
            "meta": { "type": "Category", "name": category }
        })
        edges.append({ "from": center_id, "to": cat_id, "label": "SECTOR", "color": { "color": "#64748B" }, "dashes": True, "length": 210 })

        # Related Research Papers
        kw = creator.lower() if creator else prod_name.lower()
        rel_papers = [pa for pa in store.papers if kw in str(pa.get("content.title", "")).lower() or kw in str(pa.get("content.authors", "")).lower()][:3]
        if not rel_papers:
            ind_w = [w.lower() for w in category.replace(",", " ").split() if len(w) > 3]
            for pa in store.papers:
                if any(w in str(pa.get("content.title", "")).lower() for w in ind_w):
                    rel_papers.append(pa)
                if len(rel_papers) >= 3:
                    break
        for i, pa in enumerate(rel_papers[:3]):
            paid = f"paper_{i}"
            title = str(pa.get("content.title", "Research Paper"))
            pa_url = str(pa.get("content.paper_url") or pa.get("content.github_url") or pa.get("content.pdf_url") or "")
            nodes.append({
                "id": paid,
                "label": f"📄 {title[:25]}...",
                "group": "paper",
                "title": "",
                "url": pa_url,
                "value": 20,
                "shape": "dot",
                "color": { "background": "#F59E0B", "border": "#FDE68A" },
                "font": { "color": "#FFFBEB", "size": 11 },
                "meta": { "type": "Research Paper", "title": title, "stars": pa.get("content.github_stars", 0), "authors": pa.get("content.authors", ""), "url": pa_url }
            })
            edges.append({ "from": center_id, "to": paid, "label": "POWERED_BY", "color": { "color": "#F59E0B" }, "length": 160 })

        # Related News
        rel_news = [n for n in store.news if kw in str(n.get("content.title", "")).lower() or kw in str(n.get("summary", "")).lower()][:3]
        for i, n in enumerate(rel_news):
            nid = f"news_{i}"
            n_title = str(n.get("content.title", "News Signal"))
            nodes.append({
                "id": nid,
                "label": f"📰 {n_title[:24]}...",
                "group": "news",
                "title": "",
                "url": n.get("source.url") or "",
                "value": 18,
                "shape": "dot",
                "color": { "background": "#F43F5E", "border": "#FECDD3" },
                "font": { "color": "#FFF1F2", "size": 11 },
                "meta": { "type": "News Signal", "title": n_title, "url": n.get("source.url"), "date": n.get("content.published_date", "Recent") }
            })
            edges.append({ "from": center_id, "to": nid, "label": "MENTIONED_IN", "color": { "color": "#F43F5E" }, "length": 175 })

        return web.json_response({
            "canonical_name": prod_name,
            "entity_type": "products",
            "nodes": nodes,
            "edges": edges,
            "counts": { "nodes": len(nodes), "edges": len(edges) }
        })

    # =========================================================
    # 2. RESEARCH PAPER CENTRIC GRAPH
    # =========================================================
    elif entity_type == "papers":
        paper = next((p for p in store.papers if raw_name.lower() in str(p.get("content.title", "")).lower()), None)
        if not paper:
            paper = store.papers[0] if store.papers else {}

        p_title = str(paper.get("content.title", raw_name))
        p_url = str(paper.get("content.paper_url") or paper.get("content.github_url") or paper.get("content.pdf_url") or "").strip()
        stars = paper.get("content.github_stars", 0)
        authors = str(paper.get("content.authors", "Research Team"))

        # Center Paper Node (Oval shape)
        center_id = "paper_center"
        nodes.append({
            "id": center_id,
            "label": f"📄 {p_title[:30]}...",
            "group": "paper",
            "title": "",
            "url": p_url or "/#papers",
            "value": 38,
            "shape": "ellipse",
            "margin": 14,
            "borderWidth": 2.5,
            "shadow": { "enabled": True, "color": "rgba(245, 158, 11, 0.45)", "size": 16, "x": 0, "y": 4 },
            "color": {
                "background": "#D97706",
                "border": "#FDE68A",
                "highlight": { "background": "#B45309", "border": "#FFFFFF" }
            },
            "font": { "color": "#FFFFFF", "size": 14, "face": "Inter", "bold": "true" },
            "meta": {
                "type": "Research Paper",
                "title": p_title,
                "stars": stars,
                "authors": authors,
                "url": p_url,
                "published": paper.get("content.published_date", "Recent")
            }
        })

        # GitHub Repo Node
        if paper.get("content.github_url"):
            gh_id = "github_repo_node"
            gh_url = str(paper.get("content.github_url"))
            nodes.append({
                "id": gh_id,
                "label": f"⭐ Code Repo ({stars} Stars)",
                "group": "code",
                "title": "",
                "url": gh_url,
                "value": 26,
                "shape": "box",
                "color": { "background": "#BE185D", "border": "#F472B6" },
                "font": { "color": "#FDF2F8", "size": 12 },
                "meta": { "type": "Code Repository", "stars": stars, "url": gh_url }
            })
            edges.append({ "from": center_id, "to": gh_id, "label": "OPEN_SOURCE_CODE", "color": { "color": "#DB2777" }, "length": 130 })

        # Authoring Companies / Labs
        known_labs = ["OpenAI", "DeepMind", "Anthropic", "Meta", "Google", "Microsoft", "Mistral AI", "Cohere", "Stability AI", "Hugging Face"]
        matched_labs = [lab for lab in known_labs if lab.lower() in authors.lower() or lab.lower() in p_title.lower()]
        if not matched_labs:
            matched_labs = ["Frontier AI Lab"]
        
        main_lab_id = None
        for i, lab in enumerate(matched_labs[:2]):
            lab_id = f"lab_{i}"
            if i == 0:
                main_lab_id = lab_id
            nodes.append({
                "id": lab_id,
                "label": f"🏢 {lab}",
                "group": "startup",
                "title": "",
                "url": "/#startups",
                "value": 28,
                "shape": "dot",
                "color": { "background": "#6366F1", "border": "#A5B4FC" },
                "font": { "color": "#FFFFFF", "size": 12 },
                "meta": { "type": "Research Lab", "name": lab }
            })
            edges.append({ "from": center_id, "to": lab_id, "label": "AUTHORED_BY", "color": { "color": "#6366F1" }, "length": 150 })

        # Commercial Products implementing architecture (Cross-linked to Lab)
        rel_prods = [p for p in store.products if any(w in str(p.get("description", "")).lower() for w in ["model", "llm", "transformer", "diffusion", "reasoning"])][:3]
        for i, p in enumerate(rel_prods):
            pid = f"prod_{i}"
            p_name = p.get("product_name")
            nodes.append({
                "id": pid,
                "label": f"🚀 {p_name}",
                "group": "product",
                "title": "",
                "url": p.get("source.url") or "/#products",
                "value": 20,
                "shape": "dot",
                "color": { "background": "#10B981", "border": "#6EE7B7" },
                "font": { "color": "#ECFDF5", "size": 11 },
                "meta": { "type": "Product", "name": p_name, "url": p.get("source.url") }
            })
            edges.append({ "from": center_id, "to": pid, "label": "TECH_APPLICATION", "color": { "color": "#10B981" }, "length": 185 })
            if main_lab_id and i == 0:
                # Organic cross-link between product and lab
                edges.append({ "from": main_lab_id, "to": pid, "label": "BUILDS", "color": { "color": "#10B981" }, "dashes": True, "length": 160 })

        # Research Jobs (Cross-linked to Lab)
        rel_jobs = [j for j in store.jobs if any(w in str(j.get("title", "")).lower() for w in ["research", "machine learning", "scientist", "ai"])][:3]
        for i, j in enumerate(rel_jobs):
            jid = f"job_{i}"
            j_title = str(j.get("title"))
            nodes.append({
                "id": jid,
                "label": f"💼 {j_title[:24]}...",
                "group": "job",
                "title": "",
                "url": j.get("job_url") or "",
                "value": 18,
                "shape": "dot",
                "color": { "background": "#0284C7", "border": "#7DD3FC" },
                "font": { "color": "#F0F9FF", "size": 11 },
                "meta": { "type": "Job Opening", "title": j_title, "company": j.get("content.company", ""), "location": j.get("location", "Remote"), "url": j.get("job_url") }
            })
            if main_lab_id:
                edges.append({ "from": main_lab_id, "to": jid, "label": "HIRING_TEAM", "color": { "color": "#0284C7" }, "length": 160 })
            else:
                edges.append({ "from": center_id, "to": jid, "label": "FIELD_ROLE", "color": { "color": "#0284C7" }, "length": 190 })

        return web.json_response({
            "canonical_name": p_title,
            "entity_type": "papers",
            "nodes": nodes,
            "edges": edges,
            "counts": { "nodes": len(nodes), "edges": len(edges) }
        })

    # =========================================================
    # 3. JOB ROLE CENTRIC GRAPH
    # =========================================================
    elif entity_type == "jobs":
        job = next((j for j in store.jobs if raw_name.lower() in str(j.get("title", "")).lower()), None)
        if not job:
            job = store.jobs[0] if store.jobs else {}

        j_title = str(job.get("title", raw_name))
        company = str(job.get("content.company", "Tech Company"))
        location = str(job.get("location", "Remote"))
        role_family = str(job.get("content.role_family", "Engineering"))
        job_url = str(job.get("job_url") or "").strip()

        # Center Job Node (Oval shape)
        center_id = "job_center"
        nodes.append({
            "id": center_id,
            "label": f"💼 {j_title[:28]}...",
            "group": "job",
            "title": "",
            "url": job_url or "/#jobs",
            "value": 36,
            "shape": "ellipse",
            "margin": 14,
            "borderWidth": 2.5,
            "shadow": { "enabled": True, "color": "rgba(2, 132, 199, 0.45)", "size": 16, "x": 0, "y": 4 },
            "color": {
                "background": "#0284C7",
                "border": "#7DD3FC",
                "highlight": { "background": "#0369A1", "border": "#FFFFFF" }
            },
            "font": { "color": "#FFFFFF", "size": 14, "face": "Inter", "bold": "true" },
            "meta": { "type": "Job Opening", "title": j_title, "company": company, "location": location, "role_family": role_family, "url": job_url }
        })

        # Company Node
        comp_id = f"company_{company.replace(' ', '_')}"
        nodes.append({
            "id": comp_id,
            "label": f"🏢 {company}",
            "group": "startup",
            "title": "",
            "url": "/#startups",
            "value": 30,
            "shape": "dot",
            "color": { "background": "#6366F1", "border": "#A5B4FC" },
            "font": { "color": "#FFFFFF", "size": 13 },
            "meta": { "type": "Startup", "name": company }
        })
        edges.append({ "from": center_id, "to": comp_id, "label": "OFFERED_BY", "color": { "color": "#6366F1" }, "length": 140 })

        # Role & Location Badges
        loc_id = "loc_badge"
        nodes.append({
            "id": loc_id,
            "label": f"📍 {location}",
            "group": "location",
            "title": "",
            "url": "/#jobs",
            "value": 16,
            "shape": "box",
            "color": { "background": "#1E293B", "border": "#475569" },
            "font": { "color": "#E2E8F0", "size": 11 },
            "meta": { "type": "Location", "name": location }
        })
        edges.append({ "from": center_id, "to": loc_id, "label": "BASE", "color": { "color": "#64748B" }, "dashes": True, "length": 190 })

        # Products built by company (Cross-linked to Company)
        prods = [p for p in store.products if company.lower() in str(p.get("content.startupName", "")).lower()][:3]
        for i, p in enumerate(prods):
            pid = f"prod_{i}"
            nodes.append({
                "id": pid,
                "label": f"🚀 {p.get('product_name')}",
                "group": "product",
                "title": "",
                "url": p.get("source.url") or "",
                "value": 20,
                "shape": "dot",
                "color": { "background": "#10B981", "border": "#6EE7B7" },
                "font": { "color": "#ECFDF5", "size": 11 },
                "meta": { "type": "Product", "name": p.get("product_name"), "creator": company }
            })
            edges.append({ "from": comp_id, "to": pid, "label": "BUILDS", "color": { "color": "#10B981" }, "length": 160 })
            if i == 0:
                # Job connects to product being worked on
                edges.append({ "from": center_id, "to": pid, "label": "CONTRIBUTES_TO", "color": { "color": "#10B981" }, "dashes": True, "length": 170 })

        # Relevant Research Papers
        for i, pa in enumerate(store.papers[:2]):
            paid = f"paper_{i}"
            title = str(pa.get("content.title", "Research Paper"))
            nodes.append({
                "id": paid,
                "label": f"📄 {title[:24]}...",
                "group": "paper",
                "title": "",
                "url": pa.get("content.paper_url") or "",
                "value": 18,
                "shape": "dot",
                "color": { "background": "#F59E0B", "border": "#FDE68A" },
                "font": { "color": "#FFFBEB", "size": 11 },
                "meta": { "type": "Research Paper", "title": title, "stars": pa.get("content.github_stars", 0) }
            })
            edges.append({ "from": center_id, "to": paid, "label": "DOMAIN_RESEARCH", "color": { "color": "#F59E0B" }, "length": 210 })

        return web.json_response({
            "canonical_name": j_title,
            "entity_type": "jobs",
            "nodes": nodes,
            "edges": edges,
            "counts": { "nodes": len(nodes), "edges": len(edges) }
        })

    # =========================================================
    # 4. NEWS SIGNAL CENTRIC GRAPH
    # =========================================================
    elif entity_type == "news":
        news_item = next((n for n in store.news if raw_name.lower() in str(n.get("content.title", "")).lower()), None)
        if not news_item:
            news_item = store.news[0] if store.news else {}

        n_title = str(news_item.get("content.title", raw_name))
        n_url = str(news_item.get("source.url") or "").strip()
        pub_date = str(news_item.get("content.published_date", "Recent"))
        summary = str(news_item.get("summary", ""))
        source_name = str(news_item.get("source.name", "AI News"))

        # Center News Node (Oval shape)
        center_id = "news_center"
        nodes.append({
            "id": center_id,
            "label": f"📰 {n_title[:30]}...",
            "group": "news",
            "title": "",
            "url": n_url or "/#news",
            "value": 36,
            "shape": "ellipse",
            "margin": 14,
            "borderWidth": 2.5,
            "shadow": { "enabled": True, "color": "rgba(244, 63, 94, 0.45)", "size": 16, "x": 0, "y": 4 },
            "color": {
                "background": "#E11D48",
                "border": "#FECDD3",
                "highlight": { "background": "#BE123C", "border": "#FFFFFF" }
            },
            "font": { "color": "#FFFFFF", "size": 14, "face": "Inter", "bold": "true" },
            "meta": { "type": "News Signal", "title": n_title, "date": pub_date, "summary": summary, "url": n_url, "source": source_name }
        })

        # Media Outlet Source Node
        src_id = "news_source_node"
        nodes.append({
            "id": src_id,
            "label": f"📡 {source_name}",
            "group": "source",
            "title": "",
            "url": n_url,
            "value": 18,
            "shape": "box",
            "color": { "background": "#1E293B", "border": "#475569" },
            "font": { "color": "#E2E8F0", "size": 11 },
            "meta": { "type": "Media Outlet", "name": source_name }
        })
        edges.append({ "from": center_id, "to": src_id, "label": "REPORTED_BY", "color": { "color": "#64748B" }, "dashes": True, "length": 130 })

        # Identify mentioned companies & their products (interconnected)
        for s in store.startups[:4]:
            s_name = str(s.get("content.entityName", ""))
            if s_name.lower() in n_title.lower() or s_name.lower() in summary.lower():
                sid = f"comp_{s_name.replace(' ', '_')}"
                nodes.append({
                    "id": sid,
                    "label": f"🏢 {s_name}",
                    "group": "startup",
                    "title": "",
                    "url": s.get("content.data.website") or "/#startups",
                    "value": 26,
                    "shape": "dot",
                    "color": { "background": "#6366F1", "border": "#A5B4FC" },
                    "font": { "color": "#FFFFFF", "size": 12 },
                    "meta": { "type": "Startup", "name": s_name }
                })
                edges.append({ "from": center_id, "to": sid, "label": "FEATURED_ENTITY", "color": { "color": "#6366F1" }, "length": 160 })

        return web.json_response({
            "canonical_name": n_title,
            "entity_type": "news",
            "nodes": nodes,
            "edges": edges,
            "counts": { "nodes": len(nodes), "edges": len(edges) }
        })

    # =========================================================
    # 5. STARTUP CENTRIC GRAPH (DEFAULT)
    # =========================================================
    else:
        # Exact match in store.startups to preserve real crawled startup names (e.g. DeepMark)
        exact_st = next((s for s in store.startups if str(s.get("content.entityName", "")).strip().lower() == raw_name.lower()), None)
        
        if exact_st:
            canonical = str(exact_st.get("content.entityName")).strip()
            startup_data = exact_st
        else:
            resolved = store.resolver.resolve_entity(raw_name)
            canonical = resolved if resolved else raw_name
            startup_data = next((s for s in store.startups if str(s.get("content.entityName", "")).strip().lower() == canonical.lower()), None)

        if not startup_data and canonical in SEED_CANONICAL_STARTUPS:
            seed = SEED_CANONICAL_STARTUPS[canonical]
            domain = seed.get("domain", "")
            startup_data = {
                "content.entityName": canonical,
                "content.data.website": f"https://{domain}" if domain else "",
                "source.url": f"https://{domain}" if domain else "",
                "industry": "Artificial Intelligence",
                "content.data.location": "Global / SF",
                "content.data.employeeCount": "100+ employees",
                "content.data.batch": "Frontier AI",
                "description": f"Frontier AI organization ({canonical}) developing advanced foundation models and intelligent systems."
            }
        elif not startup_data:
            startup_data = {
                "content.entityName": canonical,
                "content.data.website": "",
                "source.url": "",
                "industry": "Emerging Tech / AI",
                "content.data.location": "Global",
                "content.data.employeeCount": "Startup",
                "content.data.batch": "Active",
                "description": f"Startup entity: {canonical}."
            }

        norm = canonical.lower()
        startup_url = str(startup_data.get("content.data.website") or startup_data.get("source.url") or "").strip()

        # Fetch linked Products
        matched_prods = [
            p for p in store.products
            if norm == str(p.get("content.startupName", "")).lower()
            or norm == str(p.get("product_name", "")).lower()
            or norm in str(p.get("content.startupName", "")).lower()
            or norm in str(p.get("product_name", "")).lower()
        ]
        if not matched_prods and startup_url:
            matched_prods = [{
                "product_name": f"{canonical} Platform",
                "content.startupName": canonical,
                "content.pricingModel": "Freemium / API",
                "category": startup_data.get("industry", "AI Solution"),
                "source.url": startup_url,
                "description": startup_data.get("description", f"Core platform and solutions built by {canonical}.")
            }]

        # Fetch linked Research Papers
        matched_papers = [
            pa for pa in store.papers
            if norm in str(pa.get("content.title", "")).lower()
            or norm in str(pa.get("content.authors", "")).lower()
        ]
        if not matched_papers:
            ind_words = [w.lower() for w in str(startup_data.get("industry", "")).replace(",", " ").split() if len(w) > 3]
            for pa in store.papers:
                t_low = str(pa.get("content.title", "")).lower()
                if any(w in t_low for w in ind_words):
                    matched_papers.append(pa)
                if len(matched_papers) >= 3:
                    break
        matched_papers = matched_papers[:6]

        # Fetch linked Jobs
        matched_jobs = [
            j for j in store.jobs
            if norm in str(j.get("content.company", "")).lower()
            or norm in str(j.get("title", "")).lower()
        ]
        if not matched_jobs:
            ind_words = [w.lower() for w in str(startup_data.get("industry", "")).replace(",", " ").split() if len(w) > 3]
            for j in store.jobs:
                if any(w in str(j.get("content.role_family", "")).lower() or w in str(j.get("title", "")).lower() for w in ind_words):
                    matched_jobs.append(j)
                if len(matched_jobs) >= 3:
                    break
        matched_jobs = matched_jobs[:5]

        # Fetch linked News Signals
        matched_news = [
            n for n in store.news
            if norm in str(n.get("content.title", "")).lower()
            or norm in str(n.get("summary", "")).lower()
        ]
        if not matched_news:
            for n in store.news:
                if any(w in str(n.get("content.title", "")).lower() for w in ["ai", "funding", "startup", "model"]):
                    matched_news.append(n)
                if len(matched_news) >= 2:
                    break
        matched_news = matched_news[:4]

        # Central Startup Node (Oval shape)
        startup_id = f"startup_{canonical.replace(' ', '_')}"
        nodes.append({
            "id": startup_id,
            "label": f"🏢 {canonical}",
            "group": "startup",
            "title": "",
            "url": startup_url or f"/#startups",
            "value": 38,
            "shape": "ellipse",
            "margin": 14,
            "borderWidth": 2.5,
            "shadow": { "enabled": True, "color": "rgba(99, 102, 241, 0.45)", "size": 18, "x": 0, "y": 4 },
            "color": {
                "background": "#4F46E5",
                "border": "#C7D2FE",
                "highlight": { "background": "#4338CA", "border": "#FFFFFF" }
            },
            "font": { "color": "#FFFFFF", "size": 15, "face": "Inter", "bold": "true" },
            "meta": {
                "type": "Startup",
                "name": canonical,
                "industry": startup_data.get("industry", "Artificial Intelligence"),
                "website": startup_url,
                "location": startup_data.get("content.data.location", "Global"),
                "batch": startup_data.get("content.data.batch", "Active"),
                "description": startup_data.get("description", "")
            }
        })

        # Industry Node
        if startup_data.get("industry"):
            ind_id = f"ind_{startup_id}"
            nodes.append({
                "id": ind_id,
                "label": str(startup_data.get("industry")),
                "group": "industry",
                "title": "",
                "url": f"/#startups",
                "value": 16,
                "shape": "box",
                "color": { "background": "#312E81", "border": "#6366F1" },
                "font": { "color": "#C7D2FE", "size": 11 },
                "meta": { "type": "Industry", "name": str(startup_data.get("industry")) }
            })
            edges.append({ "from": startup_id, "to": ind_id, "label": "SECTOR", "color": { "color": "#4338CA" }, "dashes": True, "length": 190 })

        # Products Nodes (Cross-linked to research papers and jobs)
        prod_node_ids = []
        for i, p in enumerate(matched_prods):
            pid = f"prod_{i}_{str(p.get('product_name', '')).replace(' ', '_')}"
            prod_node_ids.append(pid)
            p_url = str(p.get("source.url") or startup_url).strip()
            pricing = str(p.get("content.pricingModel", "Freemium"))
            nodes.append({
                "id": pid,
                "label": f"🚀 {p.get('product_name')}",
                "group": "product",
                "title": "",
                "url": p_url or startup_url,
                "value": 22,
                "shape": "dot",
                "color": {
                    "background": "#10B981",
                    "border": "#6EE7B7",
                    "highlight": { "background": "#059669", "border": "#FFFFFF" }
                },
                "font": { "color": "#ECFDF5", "size": 12, "face": "Inter" },
                "meta": {
                    "type": "Product",
                    "name": p.get("product_name"),
                    "pricing": pricing,
                    "category": p.get("category", "Tool"),
                    "description": p.get("description", ""),
                    "url": p_url or startup_url
                }
            })
            edges.append({ "from": startup_id, "to": pid, "label": "BUILDS", "color": { "color": "#10B981" }, "length": 150 })

        # Paper Nodes (Cross-linked to products)
        for i, pa in enumerate(matched_papers):
            paid = f"paper_{i}"
            title = str(pa.get("content.title", "Research Paper"))
            pa_url = str(pa.get("content.paper_url") or pa.get("content.github_url") or pa.get("content.pdf_url") or "").strip()
            stars = pa.get("content.github_stars", 0)
            nodes.append({
                "id": paid,
                "label": f"📄 {title[:28]}...",
                "group": "paper",
                "title": "",
                "url": pa_url or startup_url,
                "value": 20,
                "shape": "dot",
                "color": {
                    "background": "#F59E0B",
                    "border": "#FDE68A",
                    "highlight": { "background": "#D97706", "border": "#FFFFFF" }
                },
                "font": { "color": "#FFFBEB", "size": 11, "face": "Inter" },
                "meta": {
                    "type": "Research Paper",
                    "title": title,
                    "stars": stars,
                    "authors": pa.get("content.authors", ""),
                    "url": pa_url
                }
            })
            edges.append({ "from": startup_id, "to": paid, "label": "RESEARCH", "color": { "color": "#F59E0B" }, "length": 180 })
            if prod_node_ids and i == 0:
                # Interconnected: Research paper feeds primary commercial product
                edges.append({ "from": paid, "to": prod_node_ids[0], "label": "TECH_BASE", "color": { "color": "#F59E0B" }, "dashes": True, "length": 160 })

        # Job Nodes
        for i, j in enumerate(matched_jobs):
            jid = f"job_{i}"
            j_title = str(j.get("title", "Job Role"))
            j_url = str(j.get("job_url") or startup_url).strip()
            nodes.append({
                "id": jid,
                "label": f"💼 {j_title[:24]}...",
                "group": "job",
                "title": "",
                "url": j_url or startup_url,
                "value": 18,
                "shape": "dot",
                "color": {
                    "background": "#0284C7",
                    "border": "#7DD3FC",
                    "highlight": { "background": "#0369A1", "border": "#FFFFFF" }
                },
                "font": { "color": "#F0F9FF", "size": 11, "face": "Inter" },
                "meta": {
                    "type": "Job Opening",
                    "title": j_title,
                    "location": j.get("location", "Remote"),
                    "role_family": j.get("content.role_family", "Engineering"),
                    "url": j_url
                }
            })
            edges.append({ "from": startup_id, "to": jid, "label": "HIRING", "color": { "color": "#0284C7" }, "length": 170 })

        # News Nodes
        for i, n in enumerate(matched_news):
            nid = f"news_{i}"
            n_title = str(n.get("content.title", "News Signal"))
            n_url = str(n.get("source.url") or "").strip()
            nodes.append({
                "id": nid,
                "label": f"📰 {n_title[:25]}...",
                "group": "news",
                "title": "",
                "url": n_url or startup_url,
                "value": 18,
                "shape": "dot",
                "color": {
                    "background": "#F43F5E",
                    "border": "#FECDD3",
                    "highlight": { "background": "#E11D48", "border": "#FFFFFF" }
                },
                "font": { "color": "#FFF1F2", "size": 11, "face": "Inter" },
                "meta": {
                    "type": "News Signal",
                    "title": n_title,
                    "date": n.get("content.published_date", "Today"),
                    "summary": n.get("summary", ""),
                    "url": n_url
                }
            })
            edges.append({ "from": startup_id, "to": nid, "label": "SIGNAL", "color": { "color": "#F43F5E" }, "length": 200 })

        return web.json_response({
            "canonical_name": canonical,
            "entity_type": "startups",
            "startup": startup_data,
            "nodes": nodes,
            "edges": edges,
            "counts": {
                "products": len(matched_prods),
                "papers": len(matched_papers),
                "jobs": len(matched_jobs),
                "news": len(matched_news),
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            }
        })


async def handle_graph_entities_list(request: web.Request) -> web.Response:
    """Returns list of available entities for a chosen category (startups, products, papers, jobs, news)."""
    from src.entity_resolution.seed_database import SEED_CANONICAL_STARTUPS
    cat_type = request.query.get("type", "startups").lower().strip()
    result = []
    seen = set()

    if cat_type in ("product", "products"):
        for p in store.products:
            name = str(p.get("product_name", "")).strip()
            if name and name not in seen:
                seen.add(name)
                result.append({"name": name, "source": p.get("content.startupName") or p.get("category", "Product")})
    elif cat_type in ("paper", "papers", "research_papers"):
        for pa in store.papers:
            title = str(pa.get("content.title", "")).strip()
            if title and title not in seen:
                seen.add(title)
                result.append({"name": title, "source": f"⭐ {pa.get('content.github_stars', 0)} Stars"})
    elif cat_type in ("job", "jobs"):
        for j in store.jobs:
            title = str(j.get("title", "")).strip()
            if title and title not in seen:
                seen.add(title)
                result.append({"name": title, "source": j.get("content.company", "Job Opening")})
    elif cat_type in ("news", "news_signals"):
        for n in store.news:
            title = str(n.get("content.title", "")).strip()
            if title and title not in seen:
                seen.add(title)
                result.append({"name": title, "source": n.get("source.name", "News Signal")})
    else:
        # Startups
        for k in SEED_CANONICAL_STARTUPS.keys():
            if k not in seen:
                seen.add(k)
                result.append({"name": k, "source": "Frontier AI", "is_seed": True})
        for s in store.startups:
            name = str(s.get("content.entityName", "")).strip()
            if name and name not in seen:
                seen.add(name)
                result.append({"name": name, "source": s.get("industry", "YC Startup"), "is_seed": False})
        result.sort(key=lambda x: (not x.get("is_seed", False), x["name"]))
        return web.json_response({"total": len(result), "entities": result})

    return web.json_response({"total": len(result), "entities": result[:200]})


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

    # Knowledge Graph API routes
    app.router.add_get("/api/graph/entity", handle_graph_entity)
    app.router.add_get("/api/graph/entities", handle_graph_entities_list)

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
    import os
    port = int(os.environ.get("PORT", 8000))
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)
