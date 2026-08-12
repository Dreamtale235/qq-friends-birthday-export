import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import auth
from auth import AuthManager, clear_saved_session


class _WritingContext:
    def storage_state(self, path):
        Path(path).write_text('{"cookies": []}', encoding="utf-8")


class AuthTestCase(unittest.TestCase):
    def test_default_does_not_check_or_save_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session_file = Path(temp_dir) / "state.json"
            session_file.write_text("sensitive", encoding="utf-8")
            manager = AuthManager()
            manager._context = Mock()

            with (
                patch.object(auth, "SESSION_FILE", session_file),
                patch.object(auth, "sync_playwright") as playwright,
            ):
                self.assertFalse(manager.check_session_valid())
                playwright.assert_not_called()
                manager._save_session()
                manager._context.storage_state.assert_not_called()
                self.assertTrue(session_file.exists())

    def test_opt_in_session_is_saved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            session_file = Path(temp_dir) / "sessions" / "state.json"
            session_file.parent.mkdir()
            with patch.object(auth, "SESSION_FILE", session_file):
                manager = AuthManager(persist_session=True)
                manager._context = _WritingContext()
                manager._save_session()
                self.assertEqual(session_file.read_text(encoding="utf-8"), '{"cookies": []}')

    def test_clear_session_is_exact_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session_file = root / "sessions" / "state.json"
            unrelated = root / "sessions" / "keep.txt"
            session_file.parent.mkdir()
            session_file.write_text("sensitive", encoding="utf-8")
            unrelated.write_text("keep", encoding="utf-8")

            with patch.object(auth, "SESSION_FILE", session_file):
                self.assertTrue(clear_saved_session())
                self.assertFalse(session_file.exists())
                self.assertTrue(unrelated.exists())
                self.assertFalse(AuthManager.clear_saved_session())


if __name__ == "__main__":
    unittest.main()
