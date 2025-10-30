"""Memorystore (Redis) Caching Service

This module provides caching capabilities for visualization data, query results,
and generated insights using Google Cloud Memorystore (Redis) for performance optimization.
"""

import json
import logging
import pickle
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import uuid
import asyncio
from contextlib import asynccontextmanager

import redis
import pandas as pd
from redis.sentinel import Sentinel
from redis.exceptions import RedisError, ConnectionError, TimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache levels with different TTL policies."""
    TEMPORARY = "temporary"      # Short-lived (5 minutes)
    SESSION = "session"          # Session-based (1 hour)
    PERSISTENT = "persistent"    # Long-lived (24 hours)
    PERMANENT = "permanent"      # Until manually cleared


class CacheType(Enum):
    """Types of cached data."""
    QUERY_RESULT = "query_result"
    CHART_DATA = "chart_data"
    DASHBOARD_CONFIG = "dashboard_config"
    INSIGHT_NARRATIVE = "insight_narrative"
    USER_PREFERENCES = "user_preferences"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    VISUALIZATION_CONFIG = "visualization_config"


@dataclass
class CacheEntry:
    """Structure for cache entries."""
    key: str
    data: Any
    cache_type: CacheType
    cache_level: CacheLevel
    created_at: datetime
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]
    size_bytes: int
    access_count: int
    last_accessed: datetime


@dataclass
class CacheStats:
    """Cache statistics and metrics."""
    total_keys: int
    total_memory_usage: int
    hit_rate: float
    miss_rate: float
    expired_keys: int
    cache_by_type: Dict[str, int]
    cache_by_level: Dict[str, int]
    average_ttl: float
    top_keys: List[Dict[str, Any]]


class MemorystoreCache:
    """High-performance caching service using Google Cloud Memorystore (Redis)."""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_db: int = 0,
        use_sentinel: bool = False,
        sentinel_hosts: Optional[List[Tuple[str, int]]] = None,
        sentinel_service: str = "mymaster",
        connection_pool_size: int = 50,
        socket_timeout: float = 5.0,
        key_prefix: str = "ai_data_analyst"
    ):
        """Initialize the Memorystore cache service.
        
        Args:
            redis_host: Redis server hostname
            redis_port: Redis server port
            redis_password: Redis authentication password
            redis_db: Redis database number
            use_sentinel: Whether to use Redis Sentinel for HA
            sentinel_hosts: List of sentinel (host, port) tuples
            sentinel_service: Sentinel service name
            connection_pool_size: Connection pool size
            socket_timeout: Socket timeout in seconds
            key_prefix: Prefix for all cache keys
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password
        self.redis_db = redis_db
        self.use_sentinel = use_sentinel
        self.sentinel_hosts = sentinel_hosts or [("localhost", 26379)]
        self.sentinel_service = sentinel_service
        self.key_prefix = key_prefix
        
        # TTL configurations in seconds
        self.ttl_config = {
            CacheLevel.TEMPORARY: 300,      # 5 minutes
            CacheLevel.SESSION: 3600,       # 1 hour
            CacheLevel.PERSISTENT: 86400,   # 24 hours
            CacheLevel.PERMANENT: None      # No expiration
        }
        
        # Initialize Redis connection
        self._initialize_redis(connection_pool_size, socket_timeout)
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        
        logger.info(f"Initialized MemorystoreCache with prefix '{key_prefix}'")
    
    def _initialize_redis(self, pool_size: int, timeout: float) -> None:
        """Initialize Redis connection with proper configuration."""
        try:
            if self.use_sentinel:
                # Use Redis Sentinel for high availability
                sentinel = Sentinel(
                    self.sentinel_hosts,
                    password=self.redis_password,
                    socket_timeout=timeout
                )
                self.redis_client = sentinel.master_for(
                    self.sentinel_service,
                    db=self.redis_db,
                    password=self.redis_password,
                    socket_timeout=timeout
                )
                logger.info(f"Connected to Redis via Sentinel: {self.sentinel_service}")
            else:
                # Direct Redis connection
                connection_pool = redis.ConnectionPool(
                    host=self.redis_host,
                    port=self.redis_port,
                    password=self.redis_password,
                    db=self.redis_db,
                    max_connections=pool_size,
                    socket_timeout=timeout,
                    decode_responses=False  # Keep binary for pickle support
                )
                self.redis_client = redis.Redis(connection_pool=connection_pool)
                logger.info(f"Connected to Redis: {self.redis_host}:{self.redis_port}")
            
            # Test connection
            self.redis_client.ping()
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {str(e)}")
            raise
    
    def _generate_cache_key(
        self, 
        cache_type: CacheType, 
        identifier: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a consistent cache key.
        
        Args:
            cache_type: Type of cached data
            identifier: Unique identifier for the data
            context: Additional context for key generation
            
        Returns:
            Generated cache key
        """
        # Create base key
        base_key = f"{self.key_prefix}:{cache_type.value}:{identifier}"
        
        # Add context hash if provided
        if context:
            context_str = json.dumps(context, sort_keys=True)
            context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
            base_key += f":{context_hash}"
        
        return base_key
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for caching.
        
        Args:
            data: Data to serialize
            
        Returns:
            Serialized data as bytes
        """
        try:
            if isinstance(data, pd.DataFrame):
                # Special handling for pandas DataFrames
                return pickle.dumps({
                    "type": "dataframe",
                    "data": data.to_dict("records"),
                    "columns": data.columns.tolist(),
                    "index": data.index.tolist()
                })
            elif isinstance(data, (dict, list, str, int, float, bool)):
                # JSON-serializable data
                return json.dumps(data, default=str).encode('utf-8')
            else:
                # Use pickle for complex objects
                return pickle.dumps(data)
                
        except Exception as e:
            logger.error(f"Failed to serialize data: {str(e)}")
            raise
    
    def _deserialize_data(self, data_bytes: bytes) -> Any:
        """Deserialize cached data.
        
        Args:
            data_bytes: Serialized data
            
        Returns:
            Deserialized data
        """
        try:
            # Try pickle first (handles all cases)
            try:
                data = pickle.loads(data_bytes)
                
                # Check if it's a DataFrame
                if isinstance(data, dict) and data.get("type") == "dataframe":
                    df = pd.DataFrame(data["data"])
                    df.columns = data["columns"]
                    df.index = data["index"]
                    return df
                
                return data
                
            except (pickle.UnpicklingError, TypeError):
                # Fall back to JSON
                return json.loads(data_bytes.decode('utf-8'))
                
        except Exception as e:
            logger.error(f"Failed to deserialize data: {str(e)}")
            raise
    
    def set_cache(
        self,
        cache_type: CacheType,
        identifier: str,
        data: Any,
        cache_level: CacheLevel = CacheLevel.SESSION,
        context: Optional[Dict[str, Any]] = None,
        custom_ttl: Optional[int] = None
    ) -> bool:
        """Store data in cache.
        
        Args:
            cache_type: Type of data being cached
            identifier: Unique identifier for the data
            data: Data to cache
            cache_level: Cache level determining TTL
            context: Additional context for key generation
            custom_ttl: Custom TTL in seconds (overrides cache_level)
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(cache_type, identifier, context)
            
            # Serialize data
            serialized_data = self._serialize_data(data)
            
            # Determine TTL
            ttl = custom_ttl if custom_ttl is not None else self.ttl_config[cache_level]
            
            # Create cache entry metadata
            entry_metadata = {
                "cache_type": cache_type.value,
                "cache_level": cache_level.value,
                "created_at": datetime.now().isoformat(),
                "context": context or {},
                "size_bytes": len(serialized_data),
                "identifier": identifier
            }
            
            # Store in Redis with pipeline for atomicity
            with self.redis_client.pipeline() as pipe:
                pipe.set(cache_key, serialized_data, ex=ttl)
                pipe.hset(f"{cache_key}:meta", mapping=entry_metadata)
                if ttl:
                    pipe.expire(f"{cache_key}:meta", ttl)
                pipe.execute()
            
            # Update statistics
            self.stats["sets"] += 1
            
            logger.debug(f"Cached data: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache: {str(e)}")
            self.stats["errors"] += 1
            return False
    
    def get_cache(
        self,
        cache_type: CacheType,
        identifier: str,
        context: Optional[Dict[str, Any]] = None,
        update_access_time: bool = True
    ) -> Optional[Any]:
        """Retrieve data from cache.
        
        Args:
            cache_type: Type of data being retrieved
            identifier: Unique identifier for the data
            context: Additional context for key generation
            update_access_time: Whether to update last access time
            
        Returns:
            Cached data if found, None otherwise
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(cache_type, identifier, context)
            
            # Get data from Redis
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data is None:
                self.stats["misses"] += 1
                return None
            
            # Deserialize data
            data = self._deserialize_data(cached_data)
            
            # Update access statistics if requested
            if update_access_time:
                try:
                    with self.redis_client.pipeline() as pipe:
                        pipe.hincrby(f"{cache_key}:meta", "access_count", 1)
                        pipe.hset(f"{cache_key}:meta", "last_accessed", datetime.now().isoformat())
                        pipe.execute()
                except:
                    pass  # Don't fail the cache hit for metadata updates
            
            # Update statistics
            self.stats["hits"] += 1
            
            logger.debug(f"Cache hit: {cache_key}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get cache: {str(e)}")
            self.stats["errors"] += 1
            return None
    
    def delete_cache(
        self,
        cache_type: CacheType,
        identifier: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Delete data from cache.
        
        Args:
            cache_type: Type of data being deleted
            identifier: Unique identifier for the data
            context: Additional context for key generation
            
        Returns:
            True if successfully deleted, False otherwise
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(cache_type, identifier, context)
            
            # Delete from Redis
            with self.redis_client.pipeline() as pipe:
                pipe.delete(cache_key)
                pipe.delete(f"{cache_key}:meta")
                result = pipe.execute()
            
            # Update statistics
            if result[0] > 0:  # Key existed and was deleted
                self.stats["deletes"] += 1
                logger.debug(f"Deleted cache: {cache_key}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete cache: {str(e)}")
            self.stats["errors"] += 1
            return False
    
    def exists_cache(
        self,
        cache_type: CacheType,
        identifier: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if data exists in cache.
        
        Args:
            cache_type: Type of data being checked
            identifier: Unique identifier for the data
            context: Additional context for key generation
            
        Returns:
            True if data exists in cache, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(cache_type, identifier, context)
            return bool(self.redis_client.exists(cache_key))
            
        except Exception as e:
            logger.error(f"Failed to check cache existence: {str(e)}")
            return False
    
    def get_cache_entry_info(
        self,
        cache_type: CacheType,
        identifier: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[CacheEntry]:
        """Get detailed information about a cache entry.
        
        Args:
            cache_type: Type of cached data
            identifier: Unique identifier for the data
            context: Additional context for key generation
            
        Returns:
            CacheEntry object with metadata, None if not found
        """
        try:
            cache_key = self._generate_cache_key(cache_type, identifier, context)
            
            # Get metadata
            metadata = self.redis_client.hgetall(f"{cache_key}:meta")
            if not metadata:
                return None
            
            # Decode metadata
            meta_dict = {k.decode('utf-8'): v.decode('utf-8') for k, v in metadata.items()}
            
            # Get TTL
            ttl = self.redis_client.ttl(cache_key)
            expires_at = None
            if ttl > 0:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            
            # Create CacheEntry
            entry = CacheEntry(
                key=cache_key,
                data=None,  # Don't load data for info query
                cache_type=CacheType(meta_dict.get("cache_type", cache_type.value)),
                cache_level=CacheLevel(meta_dict.get("cache_level", CacheLevel.SESSION.value)),
                created_at=datetime.fromisoformat(meta_dict.get("created_at", datetime.now().isoformat())),
                expires_at=expires_at,
                metadata=json.loads(meta_dict.get("context", "{}")),
                size_bytes=int(meta_dict.get("size_bytes", 0)),
                access_count=int(meta_dict.get("access_count", 0)),
                last_accessed=datetime.fromisoformat(meta_dict.get("last_accessed", meta_dict.get("created_at", datetime.now().isoformat())))
            )
            
            return entry
            
        except Exception as e:
            logger.error(f"Failed to get cache entry info: {str(e)}")
            return None
    
    def clear_cache_by_type(
        self, 
        cache_type: CacheType,
        pattern: Optional[str] = None
    ) -> int:
        """Clear all cache entries of a specific type.
        
        Args:
            cache_type: Type of cache entries to clear
            pattern: Optional pattern to match within the type
            
        Returns:
            Number of entries cleared
        """
        try:
            # Build search pattern
            if pattern:
                search_pattern = f"{self.key_prefix}:{cache_type.value}:*{pattern}*"
            else:
                search_pattern = f"{self.key_prefix}:{cache_type.value}:*"
            
            # Find matching keys
            keys = self.redis_client.keys(search_pattern)
            
            if not keys:
                return 0
            
            # Delete keys and their metadata
            with self.redis_client.pipeline() as pipe:
                for key in keys:
                    pipe.delete(key)
                    pipe.delete(f"{key}:meta")
                results = pipe.execute()
            
            # Count successful deletions
            deleted_count = sum(1 for result in results[::2] if result > 0)
            
            logger.info(f"Cleared {deleted_count} cache entries of type {cache_type.value}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to clear cache by type: {str(e)}")
            return 0
    
    def clear_expired_cache(self) -> int:
        """Clear all expired cache entries.
        
        Returns:
            Number of expired entries cleared
        """
        try:
            # Find all cache keys
            pattern = f"{self.key_prefix}:*"
            keys = self.redis_client.keys(pattern)
            
            expired_count = 0
            
            # Check each key for expiration
            with self.redis_client.pipeline() as pipe:
                for key in keys:
                    if not key.endswith(b":meta"):  # Skip metadata keys
                        ttl = self.redis_client.ttl(key)
                        if ttl == -2:  # Key doesn't exist (expired)
                            pipe.delete(key)
                            pipe.delete(f"{key}:meta")
                            expired_count += 1
                
                if expired_count > 0:
                    pipe.execute()
            
            logger.info(f"Cleared {expired_count} expired cache entries")
            return expired_count
            
        except Exception as e:
            logger.error(f"Failed to clear expired cache: {str(e)}")
            return 0
    
    def get_cache_statistics(self) -> CacheStats:
        """Get comprehensive cache statistics.
        
        Returns:
            CacheStats object with detailed metrics
        """
        try:
            # Get Redis info
            redis_info = self.redis_client.info()
            
            # Find all cache keys
            pattern = f"{self.key_prefix}:*"
            all_keys = self.redis_client.keys(pattern)
            
            # Filter out metadata keys
            data_keys = [key for key in all_keys if not key.endswith(b":meta")]
            
            # Analyze keys by type and level
            cache_by_type = {}
            cache_by_level = {}
            total_memory = 0
            total_ttl = 0
            ttl_count = 0
            
            for key in data_keys:
                try:
                    # Get key info
                    key_str = key.decode('utf-8')
                    parts = key_str.split(':')
                    
                    if len(parts) >= 3:
                        cache_type = parts[2]
                        cache_by_type[cache_type] = cache_by_type.get(cache_type, 0) + 1
                    
                    # Get metadata for cache level
                    meta_key = f"{key}:meta"
                    metadata = self.redis_client.hget(meta_key, "cache_level")
                    if metadata:
                        cache_level = metadata.decode('utf-8')
                        cache_by_level[cache_level] = cache_by_level.get(cache_level, 0) + 1
                    
                    # Get memory usage (approximate)
                    key_memory = self.redis_client.memory_usage(key) or 0
                    total_memory += key_memory
                    
                    # Get TTL
                    ttl = self.redis_client.ttl(key)
                    if ttl > 0:
                        total_ttl += ttl
                        ttl_count += 1
                        
                except:
                    continue  # Skip problematic keys
            
            # Calculate hit rate
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
            miss_rate = 1 - hit_rate
            
            # Get top keys by access count (sample)
            top_keys = []
            sample_keys = data_keys[:20]  # Sample first 20 keys
            for key in sample_keys:
                try:
                    meta_key = f"{key}:meta"
                    access_count = self.redis_client.hget(meta_key, "access_count")
                    if access_count:
                        top_keys.append({
                            "key": key.decode('utf-8'),
                            "access_count": int(access_count.decode('utf-8'))
                        })
                except:
                    continue
            
            # Sort by access count
            top_keys.sort(key=lambda x: x["access_count"], reverse=True)
            
            return CacheStats(
                total_keys=len(data_keys),
                total_memory_usage=total_memory,
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                expired_keys=0,  # Would need separate scan to count
                cache_by_type=cache_by_type,
                cache_by_level=cache_by_level,
                average_ttl=total_ttl / ttl_count if ttl_count > 0 else 0,
                top_keys=top_keys[:10]
            )
            
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {str(e)}")
            return CacheStats(
                total_keys=0,
                total_memory_usage=0,
                hit_rate=0.0,
                miss_rate=0.0,
                expired_keys=0,
                cache_by_type={},
                cache_by_level={},
                average_ttl=0.0,
                top_keys=[]
            )
    
    def invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (supports wildcards)
            
        Returns:
            Number of entries invalidated
        """
        try:
            full_pattern = f"{self.key_prefix}:*{pattern}*"
            keys = self.redis_client.keys(full_pattern)
            
            if not keys:
                return 0
            
            # Delete matching keys
            with self.redis_client.pipeline() as pipe:
                for key in keys:
                    pipe.delete(key)
                    pipe.delete(f"{key}:meta")
                results = pipe.execute()
            
            # Count successful deletions
            deleted_count = sum(1 for result in results[::2] if result > 0)
            
            logger.info(f"Invalidated {deleted_count} cache entries matching pattern: {pattern}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache pattern: {str(e)}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the cache service.
        
        Returns:
            Health check results
        """
        try:
            start_time = datetime.now()
            
            # Test basic operations
            test_key = f"{self.key_prefix}:health_check:{uuid.uuid4().hex[:8]}"
            test_data = {"health_check": True, "timestamp": start_time.isoformat()}
            
            # Test set
            self.redis_client.set(test_key, json.dumps(test_data), ex=60)
            
            # Test get
            retrieved_data = json.loads(self.redis_client.get(test_key))
            
            # Test delete
            self.redis_client.delete(test_key)
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Get Redis info
            redis_info = self.redis_client.info()
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "redis_version": redis_info.get("redis_version"),
                "connected_clients": redis_info.get("connected_clients"),
                "used_memory": redis_info.get("used_memory"),
                "used_memory_human": redis_info.get("used_memory_human"),
                "uptime_in_seconds": redis_info.get("uptime_in_seconds"),
                "stats": self.stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# High-level cache decorators and utilities
class CacheManager:
    """High-level cache management utilities."""
    
    def __init__(self, cache_service: MemorystoreCache):
        """Initialize cache manager.
        
        Args:
            cache_service: MemorystoreCache instance
        """
        self.cache = cache_service
    
    def cache_query_result(
        self,
        query_hash: str,
        result_data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_minutes: int = 60
    ) -> bool:
        """Cache query result with metadata.
        
        Args:
            query_hash: Hash of the SQL query
            result_data: Query result data
            metadata: Additional metadata
            ttl_minutes: Time to live in minutes
            
        Returns:
            True if cached successfully
        """
        return self.cache.set_cache(
            cache_type=CacheType.QUERY_RESULT,
            identifier=query_hash,
            data={"result": result_data, "metadata": metadata or {}},
            custom_ttl=ttl_minutes * 60
        )
    
    def get_cached_query_result(self, query_hash: str) -> Optional[Tuple[Any, Dict[str, Any]]]:
        """Get cached query result.
        
        Args:
            query_hash: Hash of the SQL query
            
        Returns:
            Tuple of (result_data, metadata) or None
        """
        cached_data = self.cache.get_cache(
            cache_type=CacheType.QUERY_RESULT,
            identifier=query_hash
        )
        
        if cached_data:
            return cached_data["result"], cached_data["metadata"]
        return None
    
    def cache_chart_config(
        self,
        chart_id: str,
        chart_config: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """Cache chart configuration.
        
        Args:
            chart_id: Unique chart identifier
            chart_config: Chart configuration data
            user_id: Optional user identifier
            
        Returns:
            True if cached successfully
        """
        context = {"user_id": user_id} if user_id else None
        
        return self.cache.set_cache(
            cache_type=CacheType.CHART_DATA,
            identifier=chart_id,
            data=chart_config,
            cache_level=CacheLevel.PERSISTENT,
            context=context
        )
    
    def cache_insight_narrative(
        self,
        narrative_id: str,
        narrative_data: Any,
        query_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Cache generated insight narrative.
        
        Args:
            narrative_id: Unique narrative identifier
            narrative_data: Generated narrative data
            query_context: Original query context
            
        Returns:
            True if cached successfully
        """
        return self.cache.set_cache(
            cache_type=CacheType.INSIGHT_NARRATIVE,
            identifier=narrative_id,
            data=narrative_data,
            cache_level=CacheLevel.PERSISTENT,
            context=query_context
        )


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    cache_service = MemorystoreCache(
        redis_host="localhost",
        redis_port=6379,
        key_prefix="ai_data_analyst_dev"
    )
    
    cache_manager = CacheManager(cache_service)
    
    try:
        # Test health check
        health = cache_service.health_check()
        print(f"Cache health: {health['status']}")
        
        # Test basic caching
        test_data = {"query": "SELECT * FROM sales", "results": [{"id": 1, "amount": 100}]}
        
        # Cache query result
        success = cache_manager.cache_query_result(
            query_hash="test_query_123",
            result_data=test_data,
            metadata={"columns": ["id", "amount"], "row_count": 1}
        )
        print(f"Cache set: {success}")
        
        # Retrieve cached result
        cached_result = cache_manager.get_cached_query_result("test_query_123")
        if cached_result:
            result_data, metadata = cached_result
            print(f"Cache hit: {len(result_data)} rows")
        
        # Test DataFrame caching
        import pandas as pd
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        
        cache_service.set_cache(
            cache_type=CacheType.CHART_DATA,
            identifier="test_dataframe",
            data=df,
            cache_level=CacheLevel.SESSION
        )
        
        cached_df = cache_service.get_cache(
            cache_type=CacheType.CHART_DATA,
            identifier="test_dataframe"
        )
        
        if cached_df is not None:
            print(f"DataFrame cached successfully: {cached_df.shape}")
        
        # Get cache statistics
        stats = cache_service.get_cache_statistics()
        print(f"Cache statistics:")
        print(f"  Total keys: {stats.total_keys}")
        print(f"  Hit rate: {stats.hit_rate:.2%}")
        print(f"  Memory usage: {stats.total_memory_usage} bytes")
        
        # Clean up test data
        cache_service.clear_cache_by_type(CacheType.QUERY_RESULT)
        cache_service.clear_cache_by_type(CacheType.CHART_DATA)
        
        print("Cache service test completed successfully")
        
    except Exception as e:
        print(f"Cache service test failed: {e}")