import unittest

from personalos import __version__


class FoundationTest(unittest.TestCase):
    def test_package_imports(self) -> None:
        self.assertEqual(__version__, "0.1.0")
