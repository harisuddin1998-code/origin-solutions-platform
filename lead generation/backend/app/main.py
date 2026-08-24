from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

from app.config import settings
from app.models.lead import Lead, LeadCreate, LeadUpdate
from app.models.search import SearchCreate, SearchResult
from app.services.scraper.manager import ScraperManager
from app.services.enrichment.lead_scorer import LeadScorer
from app.services.export.excel_exporter import ExcelExporter
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Lead Generation Platform...")
    app.state.scraper_manager = ScraperManager()
    app.state.lead_scorer = LeadScorer()
    await app.state.scraper_manager.initialize()
    yield
    # Shutdown
    await app.state.scraper_manager.cleanup()
    logger.info("Shutting down...")

app = FastAPI(
    title="Lead Generation Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_log(self, message: str, level: str = "INFO"):
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "type": "log",
                    "level": level,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
            except:
                pass

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Lead Generation Platform API", "status": "running"}

@app.post("/api/search")
async def start_search(search_request: SearchCreate, background_tasks: BackgroundTasks):
    """Start a new business search"""
    try:
        search_id = await app.state.scraper_manager.start_search(
            search_request.dict(),
            log_callback=lambda msg: manager.send_log(msg)
        )
        return {"search_id": search_id, "status": "started"}
    except Exception as e:
        logger.error(f"Search start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search/{search_id}/status")
async def get_search_status(search_id: str):
    """Get search progress status"""
    status = await app.state.scraper_manager.get_status(search_id)
    return status

@app.get("/api/leads")
async def get_leads(
    search_id: Optional[str] = None,
    min_score: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get leads with filtering"""
    leads = await Lead.get_all(
        search_id=search_id,
        min_score=min_score,
        category=category,
        limit=limit,
        offset=offset
    )
    return {"leads": leads, "total": len(leads)}

@app.put("/api/leads/{lead_id}")
async def update_lead(lead_id: str, lead_update: LeadUpdate):
    """Update lead information"""
    lead = await Lead.update(lead_id, lead_update.dict(exclude_unset=True))
    return lead

@app.post("/api/export")
async def export_leads(export_request: Dict):
    """Export leads to file"""
    try:
        exporter = ExcelExporter()
        file_path = await exporter.export(
            leads=export_request.get("lead_ids", []),
            format=export_request.get("format", "excel")
        )
        return FileResponse(
            file_path,
            media_type="application/octet-stream",
            filename=f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(websocket)