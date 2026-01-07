"""
RAG Application - Streamlit UI (Cortex Search Service)

Purpose:
- Simple document upload interface
- Question-answering using Cortex Search Service
- Clean, production-ready UI

Cortex Services Used:
- SPLIT_TEXT_RECURSIVE_CHARACTER: Automatic chunking
- Cortex Search Service: Hybrid search (vector + keyword)
- COMPLETE: Answer generation
"""

import streamlit as st
import logging
from datetime import datetime
from typing import Optional

# Import our modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.config import get_config
from python.document_processor import process_document, get_document_count, get_chunk_count
from python.retrieval import answer_question

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="RAG with Cortex Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state"""
    if 'uploaded_documents' not in st.session_state:
        st.session_state.uploaded_documents = []
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []


def validate_file(uploaded_file) -> tuple[bool, Optional[str]]:
    """Validate uploaded file"""
    config = get_config()
    
    # Check file extension
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    if file_ext not in config.app.upload.allowed_extensions:
        return False, f"Invalid file type. Allowed: {', '.join(config.app.upload.allowed_extensions)}"
    
    # Check file size
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > config.app.upload.max_file_size_mb:
        return False, f"File too large. Maximum size: {config.app.upload.max_file_size_mb}MB"
    
    # Check if empty
    if uploaded_file.size == 0:
        return False, "File is empty"
    
    return True, None


def render_upload_tab():
    """Render document upload interface"""
    st.markdown('<div class="main-header">📤 Upload Documents</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload meeting notes - Cortex Search Service handles chunking and indexing</div>', unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a text file",
        type=['txt'],
        help="Upload meeting notes in TXT format (max 10MB)"
    )
    
    if uploaded_file is not None:
        # Validate file
        is_valid, error_msg = validate_file(uploaded_file)
        
        if not is_valid:
            st.markdown(f'<div class="error-box">❌ {error_msg}</div>', unsafe_allow_html=True)
        else:
            # Show file info
            st.markdown(f'<div class="info-box">📄 <strong>{uploaded_file.name}</strong> ({uploaded_file.size / 1024:.1f} KB)</div>', unsafe_allow_html=True)
            
            # Process button
            if st.button("🚀 Upload & Index", type="primary"):
                with st.spinner("Uploading... Cortex Search Service will auto-chunk and index"):
                    try:
                        # Read content
                        content = uploaded_file.read().decode('utf-8')
                        
                        # Process document (just insert - Cortex handles the rest)
                        success, message, document_id = process_document(
                            uploaded_file.name,
                            content
                        )
                        
                        if success:
                            st.markdown(f'<div class="success-box">✅ {message}<br>Document ID: <code>{document_id}</code><br><br>Cortex Search Service is automatically:<br>• Chunking text using SPLIT_TEXT_RECURSIVE_CHARACTER<br>• Generating embeddings<br>• Updating search index</div>', unsafe_allow_html=True)
                            
                            # Add to session state
                            st.session_state.uploaded_documents.append({
                                'id': document_id,
                                'name': uploaded_file.name,
                                'timestamp': datetime.now()
                            })
                            
                            st.balloons()
                        else:
                            st.markdown(f'<div class="error-box">❌ {message}</div>', unsafe_allow_html=True)
                            
                    except Exception as e:
                        logger.error(f"Upload error: {e}")
                        st.markdown(f'<div class="error-box">❌ Error: {str(e)}</div>', unsafe_allow_html=True)
    
    # Show uploaded documents
    if st.session_state.uploaded_documents:
        st.markdown("---")
        st.markdown("### 📚 Uploaded Documents")
        
        for doc in st.session_state.uploaded_documents:
            with st.expander(f"📄 {doc['name']}"):
                st.write(f"**Document ID:** `{doc['id']}`")
                st.write(f"**Uploaded:** {doc['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")


def render_query_tab():
    """Render question-answering interface"""
    st.markdown('<div class="main-header">💬 Ask Questions</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Ask questions - Cortex Search Service provides hybrid search results</div>', unsafe_allow_html=True)
    
    # Check if documents uploaded
    if not st.session_state.uploaded_documents:
        st.markdown('<div class="info-box">ℹ️ Please upload documents first in the Upload tab</div>', unsafe_allow_html=True)
        return
    
    # Question input
    question = st.text_area(
        "Your Question",
        placeholder="e.g., What were the main action items from the meeting?",
        height=100
    )
    
    # Optional: Document filter
    with st.expander("⚙️ Advanced Options"):
        filter_by_doc = st.checkbox("Filter by specific document")
        selected_doc_id = None
        
        if filter_by_doc:
            doc_options = {doc['name']: doc['id'] for doc in st.session_state.uploaded_documents}
            selected_doc_name = st.selectbox("Select Document", list(doc_options.keys()))
            selected_doc_id = doc_options[selected_doc_name]
    
    # Submit button
    if st.button("🔍 Get Answer", type="primary", disabled=not question.strip()):
        with st.spinner("Searching with Cortex Search Service and generating answer..."):
            try:
                # Get answer using Cortex Search Service
                result = answer_question(question, selected_doc_id if filter_by_doc else None)
                
                # Display answer
                st.markdown("### 💡 Answer")
                st.markdown(f'<div class="success-box">{result["answer"]}</div>', unsafe_allow_html=True)
                
                # Display metadata
                metadata = result['metadata']
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Chunks Retrieved", metadata['chunks_retrieved'])
                with col2:
                    st.metric("Search Method", "Cortex Search")
                with col3:
                    st.metric("Top-K", metadata.get('top_k', 'N/A'))
                
                # Display context
                if result['context']:
                    with st.expander("📖 Retrieved Context (from Cortex Search Service)"):
                        for i, chunk in enumerate(result['context'], 1):
                            st.markdown(f"**Chunk {i}**")
                            st.markdown(f"*From: {chunk['FILENAME']}, Chunk #{chunk['CHUNK_INDEX']}*")
                            st.text(chunk['CHUNK_TEXT'][:500] + "..." if len(chunk['CHUNK_TEXT']) > 500 else chunk['CHUNK_TEXT'])
                            st.markdown("---")
                
                # Add to history
                st.session_state.query_history.append({
                    'question': question,
                    'answer': result['answer'],
                    'timestamp': datetime.now()
                })
                
            except Exception as e:
                logger.error(f"Query error: {e}")
                st.markdown(f'<div class="error-box">❌ Error: {str(e)}<br><br>Make sure Cortex Search Service is created (run sql/02_cortex_search_service.sql)</div>', unsafe_allow_html=True)


def render_sidebar():
    """Render sidebar with info"""
    with st.sidebar:
        st.markdown("## 🔍 Cortex Search RAG")
        st.markdown("**Powered by Snowflake Cortex**")
        
        st.markdown("---")
        
        st.markdown("### ℹ️ Cortex Services Used")
        st.markdown("""
        - **SPLIT_TEXT_RECURSIVE_CHARACTER**: Auto-chunking
        - **Cortex Search Service**: Hybrid search
        - **COMPLETE**: Answer generation
        """)
        
        st.markdown("---")
        
        st.markdown("### 📊 Statistics")
        try:
            doc_count = get_document_count()
            chunk_count = get_chunk_count()
            st.metric("Documents", doc_count)
            st.metric("Chunks (Auto-generated)", chunk_count)
            st.metric("Questions Asked", len(st.session_state.query_history))
        except:
            st.info("Connect to Snowflake to see stats")
        
        st.markdown("---")
        
        st.markdown("### ⚡ How It Works")
        st.info("""
        1. Upload document → Inserted into DOCUMENTS table
        2. Cortex auto-chunks via SPLIT_TEXT_RECURSIVE_CHARACTER
        3. Cortex Search Service auto-indexes
        4. Query → Hybrid search (vector + keyword)
        5. Generate answer with COMPLETE
        """)


def main():
    """Main application entry point"""
    try:
        # Initialize config
        config = get_config()
        
        # Initialize session state
        initialize_session_state()
        
        # Render sidebar
        render_sidebar()
        
        # Main content - tabs
        tab1, tab2 = st.tabs(["📤 Upload", "💬 Query"])
        
        with tab1:
            render_upload_tab()
        
        with tab2:
            render_query_tab()
            
    except FileNotFoundError as e:
        st.error(f"""
        ⚠️ Configuration Error
        
        {str(e)}
        
        Please create a `config.yaml` file with your Snowflake credentials.
        """)
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"""
        ❌ Application Error
        
        {str(e)}
        
        Please check the logs for more details.
        """)


if __name__ == "__main__":
    main()
