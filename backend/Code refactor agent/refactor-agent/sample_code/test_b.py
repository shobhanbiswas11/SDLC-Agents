import unittest
from sample_code.b import function_three, duplicate1, duplicate2, duplicate3, weird, pointless, globals_change

class TestBFunctions(unittest.TestCase):

    def test_function_three(self):
        # This test will just ensure no exceptions are raised
        try:
            function_three()
        except Exception as e:
            self.fail(f"function_three() raised {type(e).__name__} unexpectedly!")

    def test_duplicate_functions(self):
        # These tests will ensure no exceptions are raised
        try:
            duplicate1()
            duplicate2()
            duplicate3()
        except Exception as e:
            self.fail(f"Duplicate functions raised {type(e).__name__} unexpectedly!")

    def test_weird(self):
        # This test will just ensure no exceptions are raised
        try:
            weird()
        except Exception as e:
            self.fail(f"weird() raised {type(e).__name__} unexpectedly!")

    def test_pointless(self):
        # This test will just ensure no exceptions are raised
        try:
            pointless()
        except Exception as e:
            self.fail(f"pointless() raised {type(e).__name__} unexpectedly!")

    def test_globals_change(self):
        # This test will just ensure no exceptions are raised
        try:
            globals_change()
        except Exception as e:
            self.fail(f"globals_change() raised {type(e).__name__} unexpectedly!")

if __name__ == '__main__':
    unittest.main()
