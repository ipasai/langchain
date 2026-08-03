import sys
import types
import unittest


class _DummyStreamlitModule(types.ModuleType):
    pass


streamlit_stub = _DummyStreamlitModule("streamlit")
streamlit_stub.session_state = {}
streamlit_stub.markdown = lambda *args, **kwargs: None
streamlit_stub.caption = lambda *args, **kwargs: None
streamlit_stub.file_uploader = lambda *args, **kwargs: None
streamlit_stub.button = lambda *args, **kwargs: False
streamlit_stub.spinner = lambda *args, **kwargs: types.SimpleNamespace(__enter__=lambda self: None, __exit__=lambda self, exc_type, exc, tb: None)
streamlit_stub.columns = lambda *args, **kwargs: [None, None]
streamlit_stub.expander = lambda *args, **kwargs: types.SimpleNamespace(__enter__=lambda self: None, __exit__=lambda self, exc_type, exc, tb: None)
streamlit_stub.rerun = lambda: None
streamlit_stub.success = lambda *args, **kwargs: None
streamlit_stub.warning = lambda *args, **kwargs: None
streamlit_stub.error = lambda *args, **kwargs: None
streamlit_stub.info = lambda *args, **kwargs: None
streamlit_stub.tabs = lambda *args, **kwargs: []
streamlit_stub.empty = lambda *args, **kwargs: None
streamlit_stub.sidebar = None
streamlit_stub.set_page_config = lambda *args, **kwargs: None
streamlit_stub.write = lambda *args, **kwargs: None
streamlit_stub.markdown = lambda *args, **kwargs: None
sys.modules.setdefault("streamlit", streamlit_stub)
sys.modules.setdefault("streamlit.components", types.ModuleType("streamlit.components"))
sys.modules.setdefault("streamlit.components.v1", types.ModuleType("streamlit.components.v1"))

llm_factory_mod = types.ModuleType("llm_factory")
class LLMFactory:
    @staticmethod
    def get_llm(*args, **kwargs):
        return None
llm_factory_mod.LLMFactory = LLMFactory
sys.modules.setdefault("llm_factory", llm_factory_mod)

db_utils_mod = types.ModuleType("db_utils")
for name in [
    "delete_rag_document", "list_rag_documents", "list_quiz_records", "list_rag_knowledge",
    "save_quiz_record", "save_rag_document", "save_rag_knowledge", "save_quiz_bank_questions",
    "list_quiz_bank_sets", "list_quiz_bank_questions", "delete_quiz_bank_set",
    "delete_quiz_bank_question", "save_doc_unit", "list_doc_units", "update_doc_unit_teaching",
    "update_doc_unit_quiz", "delete_doc_units", "save_unit_quiz_record", "list_unit_quiz_records",
]:
    setattr(db_utils_mod, name, lambda *args, **kwargs: None)
sys.modules.setdefault("db_utils", db_utils_mod)

rag_utils_mod = types.ModuleType("rag_utils")
for name in ["build_rag_prompt", "compute_hash", "delete_document_from_chroma", "extract_text_from_file", "get_chroma_stats", "index_document", "query_knowledge", "split_text_into_chunks"]:
    setattr(rag_utils_mod, name, lambda *args, **kwargs: None)
sys.modules.setdefault("rag_utils", rag_utils_mod)
sys.modules.setdefault("langchain_core", types.ModuleType("langchain_core"))
messages_mod = types.ModuleType("langchain_core.messages")

class HumanMessage:
    def __init__(self, content):
        self.content = content

messages_mod.HumanMessage = HumanMessage
sys.modules.setdefault("langchain_core.messages", messages_mod)

from doc_analyzer import get_upload_signature, should_process_upload


class DocAnalyzerUploadStateTests(unittest.TestCase):
    def test_same_file_does_not_reprocess_after_success(self):
        state = {
            "doc_is_processing": False,
            "doc_pending_upload_signature": None,
            "doc_last_processed_signature": "report.pdf:1200",
        }

        self.assertFalse(should_process_upload("report.pdf:1200", state))

    def test_new_file_is_not_processed_until_requested(self):
        state = {
            "doc_is_processing": False,
            "doc_pending_upload_signature": None,
            "doc_last_processed_signature": "report.pdf:1200",
        }

        self.assertFalse(should_process_upload("summary.pdf:1200", state))

    def test_requested_file_continues_until_finished(self):
        state = {
            "doc_is_processing": True,
            "doc_pending_upload_signature": "report.pdf:1200",
            "doc_last_processed_signature": None,
        }

        self.assertTrue(should_process_upload("report.pdf:1200", state))

        state["doc_pending_upload_signature"] = None
        self.assertFalse(should_process_upload("report.pdf:1200", state))

    def test_get_upload_signature_uses_name_and_size(self):
        class DummyUpload:
            name = "report.pdf"
            size = 1200

        self.assertEqual(get_upload_signature(DummyUpload()), "report.pdf:1200")


if __name__ == "__main__":
    unittest.main()
