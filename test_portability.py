import tempfile
import unittest
from pathlib import Path

from app_paths import config_directory, data_directory, default_models_directory
from assistant_utils import extract_code_blocks, extract_stream_text
from model_library import discover_models, load_directories, save_directories, model_label
from app_settings import load_settings, normalize_settings, save_settings


class PortabilityTests(unittest.TestCase):
    def test_settings_are_normalized_and_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            save_settings({"temperature": 99, "cpu_threads": -1, "permission_mode": "Full Auto"}, path)
            loaded = load_settings(path)
            self.assertEqual(loaded["temperature"], 2.0)
            self.assertGreaterEqual(loaded["cpu_threads"], 1)
            self.assertEqual(loaded["permission_mode"], "Auto (Workspace)")

    def test_app_paths_are_path_objects(self):
        for path in (config_directory(), data_directory(), default_models_directory()):
            self.assertIsInstance(path, Path)
            self.assertTrue(path.is_absolute())

    def test_missing_model_folder_is_retained_for_removable_drive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "external" / "models"
            folder.parent.mkdir()
            config = root / "prefs.json"
            save_directories([folder], config)
            self.assertIn(folder.resolve(), load_directories(config))
            self.assertEqual(discover_models([folder]), [])

    def test_case_insensitive_gguf_extension_and_deduplication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = root / "Model.GGUF"
            model.write_bytes(b"gguf")
            found = discover_models([root, root])
            self.assertEqual(found, [model.resolve()])
            self.assertIn("Model.GGUF", model_label(model))

    def test_stream_chunk_shapes(self):
        self.assertEqual(extract_stream_text({"choices": [{"text": "legacy"}]}), "legacy")
        self.assertEqual(extract_stream_text({"choices": [{"delta": {"content": "new"}}]}), "new")
        self.assertEqual(extract_stream_text({}), "")

    def test_code_blocks_with_language_and_plain_fence(self):
        result = extract_code_blocks("Here\n```python\nprint('ok')\n```\n```\nhello\n```")
        self.assertEqual(result, ["print('ok')", "hello"])


if __name__ == "__main__":
    unittest.main()
