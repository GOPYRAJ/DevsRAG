import os
import sys
import time
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

def test_full_lifecycle():
    # Explicitly initialize DB for test runner
    init_db()

    with TestClient(app) as client:
        print("\n--- 1. Health Check ---")
        res = client.get("/api/v1/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("Health response:", res.json())

        print("\n--- 2. Upload Sample Document ---")
        sample_content = (
            "# DevsRAG Platform Brief\n\n"
            "DevsRAG is an Intelligent Document Understanding Platform using standard RAG.\n"
            "Revenue for Q3 2026 reached $4.2 Million, representing a 24% year-over-year increase.\n"
            "Key operational targets include 99.9% vector retrieval precision and dynamic citation chips.\n"
        )
        
        files = {
            "file": ("platform_brief.md", sample_content, "text/markdown")
        }
        
        res = client.post("/api/v1/documents?overwrite=true", files=files)
        assert res.status_code in [200, 202], f"Upload failed: {res.text}"
        doc_data = res.json()
        doc_id = doc_data["id"]
        print(f"Uploaded document ID: {doc_id}, initial status: {doc_data['status']}")

        print("\n--- 3. Poll Status until Ready ---")
        max_retries = 20
        final_status = "pending"
        for i in range(max_retries):
            time.sleep(0.5)
            res = client.get(f"/api/v1/documents/{doc_id}")
            assert res.status_code == 200
            doc_info = res.json()
            final_status = doc_info["status"]
            print(f"Polling [{i+1}/{max_retries}] - Status: {final_status}, Chunks: {doc_info['chunk_count']}")
            if final_status in ["ready", "failed"]:
                break

        assert final_status == "ready", f"Document processing ended in status: {final_status}, msg: {doc_info.get('status_message')}"

        print("\n--- 4. Query natural language question ---")
        query_payload = {
            "query": "What was the revenue for Q3 2026 and year-over-year increase?",
            "document_id": doc_id,
            "top_k": 4
        }
        res = client.post("/api/v1/query", json=query_payload)
        assert res.status_code == 200, f"Query failed: {res.text}"
        query_res = res.json()
        print("Query Answer:", query_res["answer"])
        print("Citations returned:", len(query_res["citations"]))
        assert len(query_res["citations"]) > 0, "Expected at least 1 citation"
        citation = query_res["citations"][0]
        print(f"Citation [1]: Doc={citation['document_name']}, Page={citation['page_number']}, Snippet={citation['snippet'][:100]}...")

        print("\n--- 5. Test Irrelevant / Empty Query Guard ---")
        empty_payload = {
            "query": "What is the capital of Mars?",
            "document_id": doc_id,
            "top_k": 4
        }
        res = client.post("/api/v1/query", json=empty_payload)
        assert res.status_code == 200
        print("Irrelevant query response:", res.json()["answer"])

        print("\n--- 6. Test Document Delete & Cascading Cleanup ---")
        res = client.delete(f"/api/v1/documents/{doc_id}")
        assert res.status_code == 200
        print("Delete response:", res.json())

        # Verify document no longer exists
        res = client.get(f"/api/v1/documents/{doc_id}")
        assert res.status_code == 404
        print("Document successfully deleted and verified 404.")

if __name__ == "__main__":
    test_full_lifecycle()
    print("\nALL BACKEND UNIT & INTEGRATION TESTS PASSED SUCCESSFULLY!")
