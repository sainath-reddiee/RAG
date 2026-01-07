"""
Snowflake Client Module

Purpose:
- Manage Snowflake connections with connection pooling
- Provide retry logic for transient failures
- Handle connection lifecycle and cleanup
- Singleton pattern for connection reuse

Design Decisions:
- Singleton: One connection per application instance
- Context manager: Ensures proper cleanup
- Retry logic: Handles transient network/service failures
- Logging: Track connection events for debugging
"""

import snowflake.connector
from snowflake.connector import DictCursor
from contextlib import contextmanager
import logging
import time
from typing import Optional, Dict, Any, List

from python.config import get_config

logger = logging.getLogger(__name__)


class SnowflakeClient:
    """
    Snowflake connection manager with singleton pattern.
    
    Why singleton?
    - Reuse connections across the application
    - Avoid connection overhead
    - Centralized connection management
    
    Production considerations:
    - Connection pooling for efficiency
    - Retry logic for transient failures
    - Proper error handling and logging
    - Graceful cleanup on shutdown
    """
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SnowflakeClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the client (only once due to singleton)"""
        if self._connection is None:
            self._config = get_config()
    
    def connect(self) -> snowflake.connector.SnowflakeConnection:
        """
        Establish connection to Snowflake.
        
        Returns:
            Snowflake connection object
            
        Raises:
            snowflake.connector.Error: If connection fails after retries
        """
        if self._connection is not None:
            try:
                # Test if connection is still alive
                self._connection.cursor().execute("SELECT 1")
                return self._connection
            except Exception:
                # Connection is dead, reconnect
                logger.warning("Existing connection is dead, reconnecting...")
                self._connection = None
        
        retry_config = self._config.app.retry
        sf_config = self._config.snowflake
        
        for attempt in range(retry_config.max_attempts):
            try:
                logger.info(f"Connecting to Snowflake (attempt {attempt + 1}/{retry_config.max_attempts})...")
                
                connection_params = {
                    'account': sf_config.account,
                    'user': sf_config.user,
                    'password': sf_config.password,
                    'warehouse': sf_config.warehouse,
                    'database': sf_config.database,
                    'schema': sf_config.schema,
                }
                
                if sf_config.role:
                    connection_params['role'] = sf_config.role
                
                self._connection = snowflake.connector.connect(**connection_params)
                
                logger.info("Successfully connected to Snowflake")
                return self._connection
                
            except snowflake.connector.Error as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < retry_config.max_attempts - 1:
                    # Exponential backoff
                    delay = retry_config.initial_delay * (retry_config.backoff_factor ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    logger.error("All connection attempts failed")
                    raise
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None,
        fetch: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SQL query with retry logic.
        
        Args:
            query: SQL query to execute
            params: Query parameters (for parameterized queries)
            fetch: Whether to fetch results (False for INSERT/UPDATE/DELETE)
            
        Returns:
            List of result rows as dictionaries (if fetch=True)
            None (if fetch=False)
            
        Raises:
            snowflake.connector.Error: If query fails after retries
        """
        retry_config = self._config.app.retry
        
        for attempt in range(retry_config.max_attempts):
            try:
                conn = self.connect()
                cursor = conn.cursor(DictCursor)
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch:
                    results = cursor.fetchall()
                    cursor.close()
                    return results
                else:
                    # Snowflake auto-commits by default - no explicit commit needed
                    cursor.close()
                    return None
                    
            except snowflake.connector.Error as e:
                logger.error(f"Query execution attempt {attempt + 1} failed: {e}")
                
                # Check if error is retryable
                if self._is_retryable_error(e):
                    if attempt < retry_config.max_attempts - 1:
                        delay = retry_config.initial_delay * (retry_config.backoff_factor ** attempt)
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error("All query execution attempts failed")
                        raise
                else:
                    # Non-retryable error, fail immediately
                    logger.error(f"Non-retryable error: {e}")
                    raise
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.
        
        Retryable errors:
        - Network timeouts
        - Service unavailable
        - Connection reset
        
        Non-retryable errors:
        - Authentication failures
        - SQL syntax errors
        - Permission errors
        """
        error_msg = str(error).lower()
        
        retryable_patterns = [
            'timeout',
            'connection',
            'network',
            'unavailable',
            'reset',
            'broken pipe'
        ]
        
        return any(pattern in error_msg for pattern in retryable_patterns)
    
    def close(self):
        """Close the Snowflake connection"""
        if self._connection is not None:
            try:
                self._connection.close()
                logger.info("Snowflake connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self._connection = None
    
    @contextmanager
    def cursor(self):
        """
        Context manager for cursor operations.
        
        Usage:
            with client.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
        """
        conn = self.connect()
        cursor = conn.cursor(DictCursor)
        try:
            yield cursor
        finally:
            cursor.close()


# Convenience function for getting client
def get_snowflake_client() -> SnowflakeClient:
    """
    Get the Snowflake client instance.
    
    Returns:
        SnowflakeClient instance
        
    Usage:
        from python.snowflake_client import get_snowflake_client
        client = get_snowflake_client()
        results = client.execute_query("SELECT * FROM DOCUMENTS")
    """
    return SnowflakeClient()
