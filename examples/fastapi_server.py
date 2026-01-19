"""
FastAPI Server with MemDB Integration

This example demonstrates how to integrate MemDB with FastAPI for
building high-performance real-time applications.

Use Case: Telephony system tracking active calls and sessions
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dyn_memdb import MemDB
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MemDB Telephony Server",
    description="High-performance call management system using MemDB",
    version="1.0.0",
)

# Global database instance
db: MemDB = None


class CallData(BaseModel):
    """Schema for call records"""

    caller_id: str
    callee_id: str
    status: str
    start_time: str
    duration: int = 0
    data: dict = {}


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    global db

    db = MemDB(
        db_url=os.getenv(
            "PG_DSN", "postgresql://memdb_user:memdb_pass@localhost:5432/memdb_db"
        ),
        flush_interval=30,  # Flush every 30 seconds
        evict_interval=120,  # Evict idle after 2 minutes
        max_connections=10,
    )

    await db.start()

    # Create tables
    await db.create_table(
        "calls",
        {
            "caller_id": "string",
            "callee_id": "string",
            "status": "string",
            "start_time": "timestamp",
            "duration": "integer",
        },
    )

    await db.create_table(
        "sessions",
        {"user_id": "string", "session_token": "string", "created_at": "timestamp"},
    )

    logger.info("✅ MemDB initialized and ready")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global db
    if db:
        await db.stop()
        logger.info("✅ MemDB shutdown complete")


@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "MemDB Telephony Server",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/stats", tags=["Monitoring"])
async def get_stats():
    """Get database statistics"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    stats = db.stats()
    return {
        "cache_hits": stats["cache_hits"],
        "cache_misses": stats["cache_misses"],
        "cache_hit_rate": stats["cache_hits"]
        / (stats["cache_hits"] + stats["cache_misses"] + 1),
        "cached_records": stats["cached_records"],
        "dirty_records": stats["dirty_records"],
        "total_flushes": stats["flushes"],
        "total_evictions": stats["evictions"],
        "tables": stats["tables"],
    }


# Call Management Endpoints
@app.post("/calls", tags=["Calls"])
async def create_call(call: CallData):
    """Create a new call record"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    call_id = f"{call.caller_id}_{int(datetime.utcnow().timestamp() * 1000)}"

    try:
        await db.insert(
            "calls",
            call_id,
            {
                "caller_id": call.caller_id,
                "callee_id": call.callee_id,
                "status": call.status,
                "start_time": call.start_time,
                "duration": call.duration,
                "metadata": call.data,
            },
        )

        return {
            "call_id": call_id,
            "status": "created",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/calls/{call_id}", tags=["Calls"])
async def get_call(call_id: str):
    """Get call details"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    call_data = await db.get("calls", call_id)

    if not call_data:
        raise HTTPException(status_code=404, detail="Call not found")

    return {
        "call_id": call_id,
        "data": call_data,
        "retrieved_at": datetime.utcnow().isoformat(),
    }


@app.get("/calls", tags=["Calls"])
async def list_active_calls(status: str = "active"):
    """List all active calls"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        calls = await db.query("calls", f"data->>'status' = '{status}'", limit=1000)

        return {
            "status": status,
            "total": len(calls),
            "calls": calls,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error querying calls: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/calls/{call_id}", tags=["Calls"])
async def update_call(call_id: str, call: CallData):
    """Update call status"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        await db.upsert(
            "calls",
            call_id,
            {
                "caller_id": call.caller_id,
                "callee_id": call.callee_id,
                "status": call.status,
                "start_time": call.start_time,
                "duration": call.duration,
                "metadata": call.data,
            },
        )

        return {
            "call_id": call_id,
            "status": "updated",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error updating call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/flush", tags=["Maintenance"])
async def manual_flush(background_tasks: BackgroundTasks):
    """Manual flush to persist all dirty records"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    background_tasks.add_task(db.flush)

    return {"status": "flush_initiated", "timestamp": datetime.utcnow().isoformat()}


@app.post("/evict", tags=["Maintenance"])
async def manual_evict(background_tasks: BackgroundTasks):
    """Manual eviction of idle records"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    background_tasks.add_task(db.evict_idle)

    return {"status": "eviction_initiated", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fastapi_server:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
