"""
Document Processor Module

Purpose:
- Simple document upload to Snowflake
- No manual chunking or embedding (Cortex Search Service handles it)

Design:
- Insert document into DOCUMENTS table
- Cortex Search Service automatically:
  1. Chunks via DOCUMENT_CHUNKS view
  2. Generates embeddings
  3. Updates search index
"""

import logging
import uuid
from typing import Tuple

from python.config import get_config
from python.snowflake_client import get_snowflake_client

logger = logging.getLogger(__name__)


def process_document(filename: str, content: str) -> Tuple[bool, str, str]:
    """
    Process and upload document.
    
    Cortex Search Service automatically handles:
    - Text chunking (via DOCUMENT_CHUNKS view)
    - Embedding generation
    - Search index updates
    
    Args:
        filename: Name of the uploaded file
        content: Text content of the document
        
    Returns:
        Tuple of (success, message, document_id)
    """
    try:
        # Validate content
        if not content or not content.strip():
            return False, "Document content is empty", ""
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Get Snowflake client
        client = get_snowflake_client()
        
        # Insert document
        query = """
        INSERT INTO DOCUMENTS (
            DOCUMENT_ID,
            FILENAME,
            FILE_SIZE_BYTES,
            CONTENT,
            PROCESSING_STATUS
        )
        VALUES (%s, %s, %s, %s, 'COMPLETED')
        """
        
        params = [
            document_id,
            filename,
            len(content.encode('utf-8')),
            content
        ]
        
        # Execute with proper parameter binding (not string formatting)
        try:
            client.execute_query(query, params, fetch=False)
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params types: {[type(p).__name__ for p in params]}")
            raise
        
        logger.info(f"Document {document_id} uploaded successfully")
        logger.info("Cortex Search Service will automatically chunk and index this document")
        
        return True, "Document uploaded successfully", document_id
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Error: {str(e)}", ""


def get_document_count() -> int:
    """
    Get total number of uploaded documents.
    
    Returns:
        Count of documents
    """
    try:
        client = get_snowflake_client()
        result = client.execute_query(
            "SELECT COUNT(*) AS count FROM DOCUMENTS WHERE PROCESSING_STATUS = 'COMPLETED'",
            fetch=True
        )
        return result[0]['COUNT'] if result else 0
    except Exception as e:
        logger.error(f"Error getting document count: {e}")
        return 0


def get_chunk_count() -> int:
    """
    Get total number of chunks (from view).
    
    Returns:
        Count of chunks
    """
    try:
        client = get_snowflake_client()
        result = client.execute_query(
            "SELECT COUNT(*) AS count FROM DOCUMENT_CHUNKS",
            fetch=True
        )
        return result[0]['COUNT'] if result else 0
    except Exception as e:
        logger.error(f"Error getting chunk count: {e}")
        return 0
