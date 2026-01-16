"""
Resource Optimizer - Memory and CPU optimization utilities
"""
import gc
import logging
import asyncio
import psutil
import os
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ResourceOptimizer:
    """Optimizes application resource usage"""
    
    def __init__(self):
        """Initialize resource optimizer"""
        self.last_gc_time: Optional[datetime] = None
        self.memory_threshold_mb = 200  # Trigger optimization at 200MB
        self.last_memory_check = datetime.utcnow()
        
    def get_memory_usage(self) -> Dict:
        """Get current memory usage"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            'rss_mb': round(memory_info.rss / 1024 / 1024, 2),  # Resident Set Size
            'vms_mb': round(memory_info.vms / 1024 / 1024, 2),  # Virtual Memory Size
            'percent': round(process.memory_percent(), 2)
        }
    
    def should_optimize_memory(self) -> bool:
        """Check if memory optimization is needed"""
        memory = self.get_memory_usage()
        
        # Optimize if using more than threshold
        return memory['rss_mb'] > self.memory_threshold_mb
    
    async def optimize_memory(self) -> bool:
        """Perform memory optimization"""
        try:
            initial_memory = self.get_memory_usage()
            
            # Force garbage collection
            collected = gc.collect()
            
            # Get memory after optimization
            final_memory = self.get_memory_usage()
            
            freed_mb = initial_memory['rss_mb'] - final_memory['rss_mb']
            
            if freed_mb > 1:  # Only log if significant
                logger.info(f"🧹 Memory optimization: freed {freed_mb:.2f} MB, "
                          f"collected {collected} objects")
                logger.debug(f"   Before: {initial_memory['rss_mb']:.2f} MB, "
                           f"After: {final_memory['rss_mb']:.2f} MB")
            
            self.last_gc_time = datetime.utcnow()
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Memory optimization failed: {e}")
            return False
    
    async def periodic_optimization(self):
        """Periodic resource optimization task"""
        while True:
            try:
                # Check every 5 minutes
                await asyncio.sleep(300)
                
                # Only optimize if needed
                if self.should_optimize_memory():
                    await self.optimize_memory()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic optimization: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def get_optimization_stats(self) -> Dict:
        """Get optimization statistics"""
        memory = self.get_memory_usage()
        
        return {
            'current_memory_mb': memory['rss_mb'],
            'memory_percent': memory['percent'],
            'last_gc_time': self.last_gc_time.isoformat() if self.last_gc_time else None,
            'optimization_needed': self.should_optimize_memory()
        }


# Global resource optimizer instance
resource_optimizer = ResourceOptimizer()