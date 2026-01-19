"""
Background tasks for MemDB: periodic flush and eviction
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)

async def start_background_tasks(memdb):
    """Start periodic flush and eviction tasks"""
    try:
        await asyncio.gather(
            periodic_flush_task(memdb),
            periodic_eviction_task(memdb)
        )
    except asyncio.CancelledError:
        logger.info("Background tasks cancelled")
        raise

async def periodic_flush_task(memdb):
    """Periodically flush dirty records to database"""
    while True:
        try:
            await asyncio.sleep(memdb.flush_interval)
            
            # Check for records that need flushing
            now = time.time()
            flush_needed = False
            
            async with memdb.lock:
                for table_name in memdb.dirty_records:
                    for key in memdb.dirty_records[table_name]:
                        if key in memdb.cache[table_name]:
                            entry = memdb.cache[table_name][key]
                            # Flush if record has been dirty for flush_interval
                            if entry.dirty and (now - entry.last_updated) >= memdb.flush_interval:
                                flush_needed = True
                                break
                    if flush_needed:
                        break
            
            if flush_needed:
                await memdb.flush()
                logger.debug("Periodic flush completed")
                
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in periodic flush: {e}")

async def periodic_eviction_task(memdb):
    """Periodically evict idle records from memory"""
    while True:
        try:
            await asyncio.sleep(memdb.evict_interval)
            await memdb.evict_idle()
            logger.debug("Periodic eviction completed")
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in periodic eviction: {e}")