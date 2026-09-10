"""
Data Exporter for GraphOne Intelligence Graph
Exports datasets into a multi-tab Excel workbook (6 tabs) and standalone CSV files.
"""

import logging
from pathlib import Path
from typing import List, Optional
import pandas as pd
from src.schemas.startup import StartupRecord
from src.schemas.product import ProductRecord
from src.schemas.paper import ResearchPaperRecord
from src.schemas.job import JobRecord
from src.schemas.news import NewsRecord
from src.schemas.entity_mapping import EntityMappingLogRecord
from src.config import DATA_DIR

logger = logging.getLogger(__name__)


class DataExporter:
    @staticmethod
    def export_all(
        startups: List[StartupRecord],
        products: List[ProductRecord],
        papers: List[ResearchPaperRecord],
        jobs: List[JobRecord],
        news: List[NewsRecord],
        mapping_logs: List[EntityMappingLogRecord],
        output_excel_path: Optional[Path] = None
    ) -> Path:
        """Exports all 6 vertical datasets into a 6-tab Excel workbook and individual CSVs."""
        if output_excel_path is None:
            output_excel_path = DATA_DIR / "output_intelligence_graph.xlsx"

        logger.info(f"Exporting datasets to {output_excel_path} and CSV files...")

        # 1. Startups DataFrame
        startups_data = [
            {
                "schemaVersion": s.schemaVersion,
                "recordType": s.recordType,
                "source.name": s.source.name,
                "source.url": s.source.url,
                "content.entityName": s.content.entityName,
                "content.data.employeeCount": s.content.data.employeeCount,
                "industry": s.content.data.industry,
                "description": s.content.data.description,
                "collectedAt": s.collectedAt,
            }
            for s in startups
        ]
        df_startups = pd.DataFrame(startups_data)

        # 2. Products DataFrame
        products_data = [
            {
                "schemaVersion": p.schemaVersion,
                "recordType": p.recordType,
                "source.name": p.source.name,
                "source.url": p.source.url,
                "product_name": p.content.name,
                "content.startupName": p.content.startupName,
                "content.pricingModel": p.content.pricingModel.value if hasattr(p.content.pricingModel, "value") else str(p.content.pricingModel),
                "category": p.content.category,
                "description": p.content.description,
                "collectedAt": p.collectedAt,
            }
            for p in products
        ]
        df_products = pd.DataFrame(products_data)

        # 3. Research Papers DataFrame
        papers_data = [
            {
                "schemaVersion": r.schemaVersion,
                "recordType": r.recordType,
                "content.title": r.content.title,
                "content.authors": ", ".join(r.content.authors) if isinstance(r.content.authors, list) else str(r.content.authors),
                "content.paper_url": r.content.paper_url,
                "content.github_url": r.content.github_url,
                "content.github_stars": r.content.github_stars,
                "content.published_date": r.content.published_date,
                "collectedAt": r.collectedAt,
            }
            for r in papers
        ]
        df_papers = pd.DataFrame(papers_data)

        # 4. Jobs DataFrame
        jobs_data = [
            {
                "schemaVersion": j.schemaVersion,
                "recordType": j.recordType,
                "source.name": j.source.name,
                "job_url": j.content.job_url or j.source.url,
                "title": j.content.title,
                "content.company": j.content.company,
                "content.date": j.content.date,
                "content.is_remote": j.content.is_remote,
                "content.role_family": j.content.role_family,
                "location": j.content.location,
                "collectedAt": j.collectedAt,
            }
            for j in jobs
        ]
        df_jobs = pd.DataFrame(jobs_data)

        # 5. News DataFrame
        news_data = [
            {
                "schemaVersion": n.schemaVersion,
                "recordType": n.recordType,
                "source.name": n.source.name,
                "source.url": n.content.url or n.source.url,
                "content.title": n.content.title,
                "content.published_date": n.content.published_date,
                "summary": n.content.summary,
                "category": n.content.category,
                "collectedAt": n.collectedAt,
            }
            for n in news
        ]
        df_news = pd.DataFrame(news_data)

        # 6. Entity Mapping Log DataFrame
        mapping_data = [
            {
                "raw_name": m.raw_name,
                "canonical_name": m.canonical_name,
                "confidence_score": m.confidence_score,
                "resolution_method": m.resolution_method,
                "source_context": m.source_context,
                "resolved_at": m.resolved_at,
            }
            for m in mapping_logs
        ]
        df_mapping = pd.DataFrame(mapping_data)

        # Export individual CSVs
        df_startups.to_csv(DATA_DIR / "startups.csv", index=False, encoding="utf-8")
        df_products.to_csv(DATA_DIR / "products.csv", index=False, encoding="utf-8")
        df_papers.to_csv(DATA_DIR / "research_papers.csv", index=False, encoding="utf-8")
        df_jobs.to_csv(DATA_DIR / "jobs.csv", index=False, encoding="utf-8")
        df_news.to_csv(DATA_DIR / "news.csv", index=False, encoding="utf-8")
        df_mapping.to_csv(DATA_DIR / "entity_mapping_log.csv", index=False, encoding="utf-8")

        # Export 6-tab Excel file
        with pd.ExcelWriter(output_excel_path, engine="openpyxl") as writer:
            df_startups.to_excel(writer, sheet_name="Startups", index=False)
            df_products.to_excel(writer, sheet_name="Products", index=False)
            df_papers.to_excel(writer, sheet_name="Research Papers", index=False)
            df_jobs.to_excel(writer, sheet_name="Jobs", index=False)
            df_news.to_excel(writer, sheet_name="News", index=False)
            df_mapping.to_excel(writer, sheet_name="Entity Mapping Log", index=False)

        logger.info(f"Successfully generated 6-tab Excel workbook: {output_excel_path}")
        return output_excel_path
