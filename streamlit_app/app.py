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

# Custom CSS - Modern Design
st.markdown("""
<style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Modern Answer Card */
    .answer-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3px;
        border-radius: 16px;
        margin: 1.5rem 0;
        animation: fadeIn 0.6s ease-out;
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
        transition: transform 0.3s ease;
    }
    
    .answer-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
    }
    
    .answer-content {
        background: white;
        padding: 2.5rem;
        border-radius: 14px;
        line-height: 1.9;
        font-size: 1.05rem;
        color: #2c3e50;
    }
    
    .answer-content strong {
        color: #667eea;
        font-weight: 600;
    }
    
    .answer-content code {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
    }
    
    /* Metric Cards - Force white text */
    .metric-card {
        color: white !important;
    }
    
    .metric-value {
        color: white !important;
        font-weight: 700 !important;
    }
    
    .metric-label {
        color: white !important;
        font-weight: 500 !important;
    }
    
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
    /* Better answer formatting */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .stMarkdown p {
        line-height: 1.8;
        margin-bottom: 1rem;
    }
    .stMarkdown ul, .stMarkdown ol {
        margin-left: 1.5rem;
        line-height: 1.8;
    }
    .stMarkdown li {
        margin-bottom: 0.5rem;
    }
    .stMarkdown code {
        background-color: #f5f5f5;
        padding: 0.2rem 0.4rem;
        border-radius: 0.25rem;
        font-family: 'Courier New', monospace;
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
    
    # Upload method selection
    upload_method = st.radio(
        "Choose upload method:",
        ["📄 Upload File", "✍️ Paste Text"],
        horizontal=True
    )
    
    filename = None
    content = None
    
    if upload_method == "📄 Upload File":
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
                filename = uploaded_file.name
                
                try:
                    content = uploaded_file.read().decode('utf-8')
                except Exception as e:
                    st.markdown(f'<div class="error-box">❌ Error reading file: {str(e)}</div>', unsafe_allow_html=True)
    
    else:  # Paste Text
        # Text input
        st.markdown("**Paste your text below:**")
        pasted_text = st.text_area(
            "Document Content",
            placeholder="Paste your meeting notes, document, or any text here...",
            height=300,
            label_visibility="collapsed"
        )
        
        # Document name input
        doc_name = st.text_input(
            "Document Name",
            placeholder="e.g., Meeting Notes 2024-01-07",
            help="Give your document a name"
        )
        
        if pasted_text.strip() and doc_name.strip():
            filename = f"{doc_name}.txt"
            content = pasted_text
            st.markdown(f'<div class="info-box">📝 Ready to upload: <strong>{filename}</strong> ({len(content)} characters)</div>', unsafe_allow_html=True)
        elif pasted_text.strip() and not doc_name.strip():
            st.markdown('<div class="info-box">⚠️ Please enter a document name</div>', unsafe_allow_html=True)
    
    # Process button (shown if content is ready)
    if content and filename:
        # Large upload button
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            upload_clicked = st.button("🚀 Upload & Index", type="primary", use_container_width=True, key="upload_btn")
        
        if upload_clicked:
            with st.spinner("Uploading... Cortex Search Service will auto-chunk and index"):
                try:
                    # Process document (just insert - Cortex handles the rest)
                    success, message, document_id = process_document(
                        filename,
                        content
                    )
                    
                    if success:
                        st.markdown(f'<div class="success-box">✅ {message}<br>Document ID: <code>{document_id}</code><br><br>Cortex Search Service is automatically:<br>• Chunking text using SPLIT_TEXT_RECURSIVE_CHARACTER<br>• Generating embeddings<br>• Updating search index</div>', unsafe_allow_html=True)
                        
                        # Add to session state
                        st.session_state.uploaded_documents.append({
                            'id': document_id,
                            'name': filename,
                            'timestamp': datetime.now()
                        })
                        
                        st.balloons()
                        
                        # Add prominent CTA to ask questions
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown("### 🚀 Ready to Ask Questions?")
                        st.markdown('<div class="success-box">✅ Your document is indexed and ready!<br><br><strong>👉 Click the "💬 Query" tab above to start asking questions!</strong></div>', unsafe_allow_html=True)
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
    st.markdown('<div class="sub-header">Get AI-powered answers from your documents using Cortex Search</div>', unsafe_allow_html=True)
    
    # Check if documents uploaded
    if not st.session_state.uploaded_documents:
        st.markdown('<div class="info-box">ℹ️ Please upload documents first in the Upload tab</div>', unsafe_allow_html=True)
        return
    
    # Question input with better styling
    st.markdown("### 💭 Your Question")
    question = st.text_area(
        "Type your question here",
        placeholder="Example: What were the main action items discussed in the meeting?",
        height=120,
        label_visibility="collapsed"
    )
    
    # Optional: Document filter
    with st.expander("⚙️ Advanced Options"):
        filter_by_doc = st.checkbox("Filter by specific document")
        selected_doc_id = None
        
        if filter_by_doc:
            doc_options = {doc['name']: doc['id'] for doc in st.session_state.uploaded_documents}
            selected_doc_name = st.selectbox("Select Document", list(doc_options.keys()))
            selected_doc_id = doc_options[selected_doc_name]
    
    # Large, prominent submit button
    st.markdown("<br>", unsafe_allow_html=True)
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        submit_clicked = st.button(
            "🔍 Get Answer",
            type="primary",
            disabled=not question.strip(),
            use_container_width=True,
            help="Click to search and generate answer"
        )
    
    if submit_clicked:
        with st.spinner("🔍 Searching documents and generating answer..."):
            try:
                # Get answer using Cortex Search Service
                logger.info(f"Calling answer_question with: {question[:50]}...")
                result = answer_question(question, selected_doc_id if filter_by_doc else None)
                logger.info(f"Result type: {type(result)}")
                logger.info(f"Result: {str(result)[:200]}...")
                
                # Validate result
                if not isinstance(result, dict):
                    st.error(f"❌ Unexpected response type: {type(result)}")
                    st.code(str(result))
                    logger.error(f"Result is not a dict: {result}")
                    return
                
                # Display answer with better formatting
                st.markdown("### 💡 Answer")
                
                # Get and clean answer text
                answer_text = result.get("answer", "No answer provided")
                
                # Clean escaped characters and remove code fences
                import re
                cleaned = answer_text.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
                
                # Remove any JSON code fences
                if '```' in cleaned:
                    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, re.DOTALL)
                    if match:
                        cleaned = match.group(1).strip()
                
                # Remove leading/trailing quotes if the whole thing is quoted
                if cleaned.startswith('"') and cleaned.endswith('"'):
                    cleaned = cleaned[1:-1]
                
                # Display in modern gradient card
                st.markdown(f"""
                <div class="answer-card">
                    <div class="answer-content">
                        {cleaned}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Display metadata with modern gradient cards
                st.markdown("---")
                st.markdown("### 📊 Search Metrics")
                
                metadata = result.get('metadata', {})
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card" style="background: linear-gradient(135deg, #5f72bd 0%, #9b23ea 100%); 
                                box-shadow: 0 8px 20px rgba(95, 114, 189, 0.4);">
                        <div class="metric-value">{metadata.get('chunks_retrieved', 0)}</div>
                        <div class="metric-label">📦 Chunks Retrieved</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                                box-shadow: 0 8px 20px rgba(17, 153, 142, 0.4);">
                        <div class="metric-value">Hybrid</div>
                        <div class="metric-label">🔍 Search Method</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card" style="background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
                                box-shadow: 0 8px 20px rgba(238, 9, 121, 0.4);">
                        <div class="metric-value">{metadata.get('top_k', 5)}</div>
                        <div class="metric-label">🎯 Top-K</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Display context - COLLAPSED by default for clean RAG experience
                context = result.get('context', [])
                if context and len(context) > 0:
                    st.markdown("---")
                    with st.expander(f"📚 View Source Context ({len(context)} chunks retrieved)", expanded=False):
                        st.caption("The answer above was generated from these relevant text chunks")
                        
                        for i, chunk in enumerate(context, 1):
                            st.markdown(f"**📄 Chunk {i}** - *{chunk.get('FILENAME', 'Unknown')}* (Position #{chunk.get('CHUNK_INDEX', '?')})")  
                            
                            # Show chunk text in a clean way
                            chunk_text = chunk.get('CHUNK_TEXT', '')
                            if len(chunk_text) > 500:
                                st.text_area(
                                    f"chunk_{i}",
                                    chunk_text[:500] + "...",
                                    height=100,
                                    disabled=True,
                                    label_visibility="collapsed"
                                )
                                st.caption(f"📏 Showing first 500 of {len(chunk_text)} characters")
                            else:
                                st.text_area(
                                    f"chunk_{i}",
                                    chunk_text,
                                    height=80,
                                    disabled=True,
                                    label_visibility="collapsed"
                                )
                            
                            if i < len(context):
                                st.markdown("---")
                else:
                    st.markdown("---")
                    st.info("ℹ️ No context chunks were retrieved for this query.")
                
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
        
        # How it works - moved to sidebar (top right)
        st.markdown("### ℹ️ How It Works")
        with st.expander("RAG Pipeline", expanded=False):
            st.markdown("""
            1. 📝 **Upload** documents
            2. ⚙️ **Auto-chunk** via SPLIT_TEXT
            3. 📊 **Index** with Cortex Search
            4. 🔍 **Search** with hybrid algorithm
            5. 🤖 **Generate** answer with AI
            """)
        
        with st.expander("Cortex Services", expanded=False):
            st.markdown("""
            - **SPLIT_TEXT_RECURSIVE_CHARACTER**: Auto-chunking
            - **Cortex Search Service**: Hybrid search
            - **AI_COMPLETE**: Answer generation
            """)
        
        st.markdown("---")
        
        st.markdown("### 📊 Statistics")
        try:
            doc_count = get_document_count()
            chunk_count = get_chunk_count()
            st.metric("📄 Documents", doc_count)
            st.metric("📦 Chunks", chunk_count)
            st.metric("💬 Questions", len(st.session_state.query_history))
        except Exception as e:
            st.caption("⚠️ Unable to load statistics")
            logger.error(f"Stats error: {e}")
        
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
        
        # Initialize active tab if not set
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 'upload'
        
        # Render sidebar
        render_sidebar()
        
        # ============================================================================
        # HEADER SECTION - Clean and Simple
        # ============================================================================
        st.markdown("""
        <div style="text-align: center; padding: 1.5rem 0 1rem 0;">
            <h1 style="color: #1f77b4; font-size: 2.2rem; margin-bottom: 0.5rem;">
                ❄️ Snowflake Cortex RAG
            </h1>
            <p style="font-size: 1rem; color: #666; margin-bottom: 0.5rem;">
                AI-Powered Document Q&A • Created by <strong>Sainath Reddy</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        
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
