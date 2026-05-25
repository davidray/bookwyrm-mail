import unittest

from mailwyrm.models import GMAIL_MODIFY_SCOPE, GMAIL_READONLY_SCOPE
from mailwyrm.oauth import scope_for_name


class OAuthTest(unittest.TestCase):
    def test_scope_for_name(self) -> None:
        self.assertEqual(scope_for_name("readonly"), GMAIL_READONLY_SCOPE)
        self.assertEqual(scope_for_name("modify"), GMAIL_MODIFY_SCOPE)


if __name__ == "__main__":
    unittest.main()
