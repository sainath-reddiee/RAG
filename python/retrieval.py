"""
RAG Pipeline Module using Cortex Search Service

Purpose:
- Perform RAG using Cortex Search Service
- No manual vector search needed
- Hybrid search (vector + keyword + reranking)

Design:
- Use SNOWFLAKE.CORTEX.SEARCH_PREVIEW() for retrieval
- Use SNOWFLAKE.CORTEX.AI_COMPLETE() for generation (latest version)
- Simple and efficient
"""

import logging
from typing import Dict, Any, Optional, List

from python.config import get_config
from python.snowflake_client import get_snowflake_client

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG pipeline using Cortex Search Service.
    
    Pipeline:
    1. Search using Cortex Search Service (hybrid search)
    2. Construct prompt with retrieved context
    3. Generate answer using Cortex Complete
    """
    
    def __init__(self):
        """Initialize RAG pipeline"""
        self.config = get_config()
        self.client = get_snowflake_client()
        
        # Configuration
        self.top_k = self.config.app.retrieval.top_k
        self.llm_model = self.config.app.generation.model
        self.max_tokens = self.config.app.generation.max_tokens
        self.temperature = self.config.app.generation.temperature
        
        logger.info(f"Initialized RAG pipeline with Cortex Search Service")
    
    def answer_question(
        self, 
        question: str, 
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer question using Cortex Search Service + Complete.
        
        Args:
            question: User's question
            document_id: Optional filter by document ID
            
        Returns:
            Dictionary with answer, context, and metadata
        """
        logger.info(f"Answering question: {question[:100]}...")
        
        # Step 1: Search using Cortex Search Service
        search_results = self._search(question, document_id)
        
        if not search_results:
            return {
                'answer': "I don't have enough information to answer this question. Please upload relevant documents first.",
                'context': [],
                'metadata': {
                    'chunks_retrieved': 0,
                    'search_method': 'cortex_search_service'
                }
            }
        
        # Step 2: Construct prompt
        prompt = self._construct_prompt(question, search_results)
        
        # Step 3: Generate answer
        answer = self._generate_answer(prompt)
        
        return {
            'answer': answer,
            'context': search_results,
            'metadata': {
                'chunks_retrieved': len(search_results),
                'search_method': 'cortex_search_service',
                'top_k': self.top_k
            }
        }
    
    def _search(
        self, 
        question: str, 
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using Cortex Search Service.
        
        Args:
            question: Search query
            document_id: Optional document filter
            
        Returns:
            List of search results with chunks and metadata
        """
        try:
            # Use Cortex Search Service with SEARCH_PREVIEW function
            # Syntax: SNOWFLAKE.CORTEX.SEARCH_PREVIEW('service_name', 'json_params')
            if document_id:
                # Search with document filter
                query_params = {
                    "query": question,
                    "columns": ["CHUNK_TEXT", "DOCUMENT_ID", "FILENAME", "CHUNK_INDEX"],
                    "filter": {"@eq": {"DOCUMENT_ID": document_id}},
                    "limit": self.top_k
                }
            else:
                # Search across all documents
                query_params = {
                    "query": question,
                    "columns": ["CHUNK_TEXT", "DOCUMENT_ID", "FILENAME", "CHUNK_INDEX"],
                    "limit": self.top_k
                }
            
            # Convert to JSON string
            import json
            query_params_json = json.dumps(query_params)
            
            query = """
            SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                'MEETING_NOTES_SEARCH',
                %s
            ) AS search_results
            """
            
            params = [query_params_json]
            
            logger.info(f"Executing search with params: {query_params}")
            result = self.client.execute_query(query, params, fetch=True)
            
            if result and len(result) > 0:
                # The result is a single row with SEARCH_RESULTS column containing JSON
                search_results_json = result[0].get('SEARCH_RESULTS')
                
                if search_results_json:
                    logger.info(f"Raw search results: {search_results_json[:500]}...")
                    
                    # Parse JSON results
                    if isinstance(search_results_json, str):
                        search_data = json.loads(search_results_json)
                    else:
                        search_data = search_results_json
                    
                    results = search_data.get('results', [])
                    logger.info(f"Cortex Search Service returned {len(results)} chunks")
                    
                    # Normalize column names to uppercase (Snowflake convention)
                    normalized_results = []
                    for r in results:
                        normalized = {k.upper(): v for k, v in r.items()}
                        normalized_results.append(normalized)
                    
                    return normalized_results
                else:
                    logger.warning("SEARCH_RESULTS column is empty")
                    return []
            else:
                logger.warning("No results from query execution")
                return []
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            # Check if search service exists
            if "does not exist" in str(e).lower():
                logger.error("Cortex Search Service not found. Please run 02_cortex_search_service.sql")
            return []
    
    def _construct_prompt(
        self, 
        question: str, 
        search_results: List[Dict[str, Any]]
    ) -> str:
        """
        Construct prompt with system instructions and context.
        
        Args:
            question: User's question
            search_results: Retrieved chunks from search
            
        Returns:
            Formatted prompt
        """
        # System instruction - Clean markdown output
        system_instruction = """You are a helpful assistant that answers questions based on the provided context.

IMPORTANT RULES:
1. Provide COMPREHENSIVE answers using ALL relevant information from the context
2. Structure your answer with clear paragraphs and bullet points
3. Use simple, readable formatting - NO JSON, NO code blocks
4. Always cite sources at the end like: (Source: filename, Chunk #number)
5. If the context doesn't contain enough information, say "I don't have enough information to answer this question"
6. Do NOT make up information that isn't in the context
7. Be thorough and detailed

FORMATTING:
- Write in clear, natural language
- Use bullet points for lists
- Keep it readable and well-organized
- Add citations at the end of relevant points"""
        
        # Format context
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"[Document: {result['FILENAME']}, Chunk {result['CHUNK_INDEX']}]\n"
                f"{result['CHUNK_TEXT']}\n"
            )
        
        context = "\n---\n".join(context_parts)
        
        # Construct final prompt
        prompt = f"""{system_instruction}

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:"""
        
        return prompt
    
    def _generate_answer(self, prompt: str) -> str:
        """
        Generate answer using Snowflake Cortex Complete.
        
        Args:
            prompt: Formatted prompt with context
            
        Returns:
            Generated answer
        """
        try:
            # Use Cortex AI_COMPLETE (latest version)
            # Must use named parameters: model, prompt, model_parameters
            query = """
            SELECT AI_COMPLETE(
                model => %s,
                prompt => %s,
                model_parameters => OBJECT_CONSTRUCT(
                    'max_tokens', %s,
                    'temperature', %s
                )
            ) AS answer
            """
            
            params = [self.llm_model, prompt, self.max_tokens, self.temperature]
            
            result = self.client.execute_query(query, params, fetch=True)
            
            if not result or 'ANSWER' not in result[0]:
                logger.error("Failed to generate answer")
                return "I encountered an error while generating the answer. Please try again."
            
            answer = result[0]['ANSWER']
            
            # Log token usage (approximate)
            approx_prompt_tokens = len(prompt) // 4
            approx_answer_tokens = len(answer) // 4
            logger.info(
                f"Generated answer (~{approx_prompt_tokens} prompt tokens, "
                f"~{approx_answer_tokens} completion tokens)"
            )
            
            return answer
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return "I encountered an error while generating the answer. Please try again."


# Convenience function
def answer_question(question: str, document_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Answer a question using Cortex Search Service + Complete.
    
    Args:
        question: User's question
        document_id: Optional document ID filter
        
    Returns:
        Answer dictionary with answer, context, and metadata
        
    Usage:
        from python.retrieval import answer_question
        
        result = answer_question("What was discussed in the meeting?")
        print(result['answer'])
        print(f"Retrieved {result['metadata']['chunks_retrieved']} chunks")
    """
    pipeline = RAGPipeline()
    return pipeline.answer_question(question, document_id)
