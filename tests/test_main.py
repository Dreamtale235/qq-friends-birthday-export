import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import main


class MainTestCase(unittest.TestCase):
    def test_chromium_check_accepts_configured_headful_browser(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "chromium-1234").mkdir()
            with patch.dict(
                main.os.environ,
                {"PLAYWRIGHT_BROWSERS_PATH": temp_dir},
                clear=False,
            ):
                self.assertTrue(main._check_chromium())

    def test_clear_session_exits_before_browser_check(self):
        output = io.StringIO()
        with (
            patch("main.clear_saved_session", return_value=True),
            patch("main._check_chromium") as check_chromium,
            redirect_stdout(output),
        ):
            main.main(["--clear-session"])

        check_chromium.assert_not_called()
        self.assertIn("已清除", output.getvalue())

    def test_cli_passes_explicit_session_choice(self):
        with (
            patch("main._check_chromium", return_value=True),
            patch("run_cli.run_cli") as run_cli,
        ):
            main.main(["--cli", "--remember-session"])

        run_cli.assert_called_once_with(remember_session=True)


if __name__ == "__main__":
    unittest.main()
