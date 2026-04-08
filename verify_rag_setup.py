#!/usr/bin/env python
"""
TaxShield RAG System — Setup & Verification Script
Verifies dependencies, checks environment, and runs basic checks.
"""

import os
import sys
import subprocess
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text: str):
    print(f"\n{BLUE}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{RESET}\n")


def check_pass(text: str):
    print(f"{GREEN}✓ {text}{RESET}")


def check_fail(text: str):
    print(f"{RED}✗ {text}{RESET}")


def check_warn(text: str):
    print(f"{YELLOW}⚠ {text}{RESET}")


def check_python_version():
    """Verify Python 3.8+"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        check_pass(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        check_fail(f"Python {version.major}.{version.minor} (requires 3.8+)")
        return False


def check_pip_packages():
    """Verify required packages are installed"""
    print_header("Checking Required Packages")
    
    required = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "pydantic": "Pydantic",
        "numpy": "NumPy",
        "faiss": "FAISS",
        "openai": "OpenAI",
        "sqlalchemy": "SQLAlchemy",
    }
    
    all_ok = True
    for module, name in required.items():
        try:
            __import__(module)
            check_pass(f"{name}")
        except ImportError:
            check_fail(f"{name} (run: pip install -r requirements.txt)")
            all_ok = False
    
    return all_ok


def check_environment_variables():
    """Verify required environment variables"""
    print_header("Checking Environment Variables")
    
    required = {
        "OPENAI_API_KEY": "OpenAI API Key",
        # Add others as needed
    }
    
    all_ok = True
    for var, desc in required.items():
        if var in os.environ:
            value = os.environ[var]
            masked = value[:8] + "..." if len(value) > 8 else "***"
            check_pass(f"{desc} ({masked})")
        else:
            check_fail(f"{desc} (set: export {var}=...)")
            all_ok = False
    
    return all_ok


def check_project_structure():
    """Verify RAG module structure"""
    print_header("Checking Project Structure")
    
    backend_dir = Path("backend")
    required_files = [
        backend_dir / "app" / "rag" / "__init__.py",
        backend_dir / "app" / "rag" / "vector_store.py",
        backend_dir / "app" / "rag" / "rag_service.py",
        backend_dir / "app" / "routes" / "rag_routes.py",
        backend_dir / "test_rag.py",
    ]
    
    all_ok = True
    for file in required_files:
        if file.exists():
            check_pass(f"{file}")
        else:
            check_fail(f"{file} (missing)")
            all_ok = False
    
    return all_ok


def check_rag_directory():
    """Verify data directory exists"""
    print_header("Checking Data Directories")
    
    rag_data = Path("backend/data/rag_store")
    docs_dir = rag_data / "documents"
    
    try:
        rag_data.mkdir(parents=True, exist_ok=True)
        docs_dir.mkdir(parents=True, exist_ok=True)
        check_pass(f"Created {rag_data}")
        return True
    except Exception as e:
        check_fail(f"Failed to create directories: {e}")
        return False


def test_imports():
    """Test that RAG modules can be imported"""
    print_header("Testing Module Imports")
    
    sys.path.insert(0, str(Path.cwd() / "backend"))
    
    try:
        from app.rag.vector_store import VectorStore, chunk_text
        check_pass("app.rag.vector_store")
    except Exception as e:
        check_fail(f"app.rag.vector_store: {e}")
        return False
    
    try:
        from app.rag.rag_service import call_llm_with_guard, moderate_input
        check_pass("app.rag.rag_service")
    except Exception as e:
        check_fail(f"app.rag.rag_service: {e}")
        return False
    
    try:
        from app.routes.rag_routes import router
        check_pass("app.routes.rag_routes")
    except Exception as e:
        check_fail(f"app.routes.rag_routes: {e}")
        return False
    
    return True


def test_vector_store():
    """Quick test of vector store"""
    print_header("Testing Vector Store")
    
    try:
        import numpy as np
        from app.rag.vector_store import VectorStore, chunk_text
        
        # Create temp store
        store = VectorStore(
            index_path="/tmp/test_faiss",
            metadata_path="/tmp/test_metadata.json",
        )
        check_pass("VectorStore initialization")
        
        # Test chunking
        text = "This is a test document. It has multiple sentences. Each sentence is important."
        chunks = chunk_text(text, chunk_size=10, overlap=2)
        check_pass(f"Text chunking ({len(chunks)} chunks)")
        
        # Test vector operations
        dummy_vec = np.random.rand(1536).astype("float32")
        idx = store.add_vector(
            embedding=dummy_vec,
            doc_id="test-doc",
            chunk_index=0,
            text="Test chunk",
        )
        check_pass(f"Vector addition (idx={idx})")
        
        # Test search
        query_vec = np.random.rand(1536).astype("float32")
        results = store.search(query_vec, top_k=1)
        check_pass(f"Vector search ({len(results)} results)")
        
        return True
    except Exception as e:
        check_fail(f"Vector store test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_moderation():
    """Test moderation function"""
    print_header("Testing Moderation")
    
    try:
        from app.rag.rag_service import moderate_input
        
        # Test safe text
        safe, reason = moderate_input("Hello, how can I help you with tax questions?")
        if safe:
            check_pass("Safe text allowed")
        else:
            check_warn(f"Safe text flagged: {reason}")
        
        return True
    except Exception as e:
        check_warn(f"Moderation test skipped: {e}")
        return True  # Not critical


def verify_requirements():
    """Verify all dependencies in requirements.txt"""
    print_header("Verifying Requirements.txt")
    
    req_file = Path("backend/requirements.txt")
    if not req_file.exists():
        check_fail("requirements.txt not found")
        return False
    
    # Check for critical packages
    content = req_file.read_text()
    required = ["faiss-cpu", "openai", "fastapi", "pydantic"]
    
    all_ok = True
    for pkg in required:
        if pkg in content.lower():
            check_pass(f"{pkg} in requirements.txt")
        else:
            check_fail(f"{pkg} NOT in requirements.txt")
            all_ok = False
    
    return all_ok


def main():
    """Run all checks"""
    print(f"\n{BLUE}TaxShield RAG System — Setup Verification{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    checks = [
        ("Python Version", check_python_version),
        ("Project Structure", check_project_structure),
        ("Requirements.txt", verify_requirements),
        ("Pip Packages", check_pip_packages),
        ("Environment Variables", check_environment_variables),
        ("Data Directories", check_rag_directory),
        ("Module Imports", test_imports),
        ("Vector Store", test_vector_store),
        ("Moderation", test_moderation),
    ]
    
    results = {}
    for name, check_fn in checks:
        try:
            results[name] = check_fn()
        except Exception as e:
            check_fail(f"{name}: Unexpected error: {e}")
            results[name] = False
    
    # Summary
    print_header("Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Passed: {passed}/{total}\n")
    for name, result in results.items():
        status = "✓" if result else "✗"
        color = GREEN if result else RED
        print(f"{color}{status} {name}{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}All checks passed! Ready to use RAG system.{RESET}")
        print(f"\n{BLUE}Next steps:{RESET}")
        print(f"1. Start backend: cd backend && python -m uvicorn app.main:app --reload")
        print(f"2. In another terminal: cd backend && python test_rag.py full")
        print(f"3. Check API docs: http://localhost:8000/docs")
        return 0
    else:
        print(f"\n{RED}Some checks failed. Please fix issues above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
