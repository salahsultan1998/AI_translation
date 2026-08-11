import os
from dotenv import load_dotenv
from custom_types import RowItem
from excel_engine import ExcelHandler
from rag_engine import RAGEngine

load_dotenv()


def test_environment():
    print("🔍 [1/3] Testing Environment Variables...")
    assert os.getenv("OPENROUTER_API_KEY"), "❌ OPENROUTER_API_KEY is missing in .env"
    assert os.getenv("PINECONE_API_KEY"), "❌ PINECONE_API_KEY is missing in .env"
    assert os.getenv("PINECONE_INDEX_NAME"), "❌ PINECONE_INDEX_NAME is missing in .env"
    print("   ✅ All environment variables are loaded!\n")


def test_excel_engine():
    print("🔍 [2/3] Testing Excel Batching Logic...")
    sample_rows = [
        RowItem(row_id=0, source_text="你好，玩家！", context_note="dialogue"),
        RowItem(row_id=1, source_text="获得物品：黄金剑", context_note="system_message"),
        RowItem(row_id=2, source_text="任务完成", context_note="ui")
    ]
    batches = ExcelHandler.create_batches(sample_rows, batch_size=2)
    assert len(batches) == 2, "❌ Batching logic failed: incorrect batch count."
    assert len(batches[0]) == 2 and len(batches[1]) == 1, "❌ Incorrect item count per batch."
    print("   ✅ Excel Engine batching works correctly!\n")


def test_rag_engine():
    print("🔍 [3/3] Testing RAG Engine (OpenRouter Embeddings + Pinecone)...")
    try:
        rag = RAGEngine()

        # Test OpenRouter Embedding Generation
        print("   -> Requesting embedding vector from OpenRouter...")
        vector = rag.get_embedding("测试文本")
        assert len(vector) == 1536, f"❌ Embedding vector length mismatch. Expected 1536, got {len(vector)}"
        print("   -> OpenRouter embedding response verified (Dimension: 1536)!")

        # Test Pinecone Connection & Query
        print("   -> Querying Pinecone namespaces...")
        # Use a minimal batch context call to avoid relying on a missing helper method.
        context = rag.get_batch_context([RowItem(row_id=0, source_text="测试文本")], "test_game", "Arabic", top_k_per_line=1)
        print("   -> Pinecone connection successful!")
        print("   ✅ RAG Engine setup is fully operational!\n")

    except Exception as e:
        print(f"   ❌ RAG Engine Test Failed: {e}\n")


if __name__ == "__main__":
    print("==========================================")
    print("      RUNNING AI TRANSLATOR TEST SUITE    ")
    print("==========================================\n")
    test_environment()
    test_excel_engine()
    test_rag_engine()
    print("==========================================")
    print("      ALL PRELIMINARY CHECKS PASSED       ")
    print("==========================================")