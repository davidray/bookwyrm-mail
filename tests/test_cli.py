import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from mailwyrm.cli import ensure_labels_command
from mailwyrm.models import GMAIL_READONLY_SCOPE, GmailToken
from mailwyrm.store import write_token


class CliTest(unittest.TestCase):
    def test_ensure_labels_requires_modify_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"MAILWYRM_HOME": temp_dir}):
                write_token(
                    Path(temp_dir) / "gmail-token.json",
                    GmailToken(
                        access_token="token",
                        expires_at=9999999999,
                        scope=GMAIL_READONLY_SCOPE,
                    ),
                )

                with patch.object(sys, "stderr", StringIO()) as stderr:
                    result = ensure_labels_command(Path("client_secret.json"))

        self.assertEqual(result, 1)
        self.assertIn("gmail.modify", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
