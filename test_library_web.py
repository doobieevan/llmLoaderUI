import tempfile
import unittest
from pathlib import Path

from model_library import discover_models, load_directories, save_directories
from web_research import SearchLinkParser, search_url, validate_http_url


class ModelLibraryTests(unittest.TestCase):
    def test_discover_gguf_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "nested").mkdir()
            (root / "nested" / "small.gguf").write_bytes(b"gguf")
            (root / "notes.txt").write_text("ignore")
            self.assertEqual([p.name for p in discover_models([root])], ["small.gguf"])

    def test_projector_gguf_files_are_not_chat_models(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            names = (
                "chat-model.gguf",
                "mmproj-model-f16.gguf",
                "mmproj-Qwen-vision-BF16.GGUF",
                "small.gguf",
            )
            for name in names:
                (root / name).write_bytes(b"gguf")
            discovered = {path.name for path in discover_models([root])}
            self.assertEqual(discovered, {"chat-model.gguf", "small.gguf"})
            self.assertTrue((root / "mmproj-model-f16.gguf").is_file())

    def test_persist_and_load_external_model_folders(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folders = [root / "disk-a", root / "disk-b"]
            for folder in folders:
                folder.mkdir()
            config = root / "settings" / "models.json"
            save_directories(folders, config)
            loaded = load_directories(config)
            self.assertTrue(all(folder.resolve() in loaded for folder in folders))

    def test_unavailable_directory_is_ignored(self):
        self.assertEqual(discover_models([Path("Z:/definitely-not-present")]), [])


class WebResearchTests(unittest.TestCase):
    def test_search_engine_urls(self):
        self.assertIn("google.com/search", search_url("hello", "Google"))
        self.assertIn("bing.com/search", search_url("hello", "Bing"))
        self.assertIn("dogpile.com", search_url("hello", "Dogpile"))
        self.assertIn("duckduckgo.com", search_url("hello", "DuckDuckGo"))

    def test_reject_non_http_private_and_embedded_credentials(self):
        for url in ("file:///C:/secret.txt", "javascript:alert(1)", "https://user:pass@example.com/", "http://127.0.0.1/", "http://localhost/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_http_url(url)

    def test_search_parser_extracts_result_url(self):
        parser = SearchLinkParser()
        parser.feed('<a class="result__a" href="https://example.com/page">Useful page</a>')
        self.assertEqual(parser.links, [("Useful page", "https://example.com/page")])


if __name__ == "__main__":
    unittest.main()
