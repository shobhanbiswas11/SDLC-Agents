import unittest
from sample_code.e import do_stuff, generate_random_array, calculate_and_print_sum, process_array, loop_with_special_case, read_file

class TestEModule(unittest.TestCase):

    def test_do_stuff(self):
        self.assertEqual(do_stuff(60), 2450)
        self.assertEqual(do_stuff(40), 2440)

    def test_generate_random_array(self):
        result = generate_random_array()
        self.assertEqual(len(result), 25)
        for num in result:
            self.assertGreaterEqual(num, 1)
            self.assertLessEqual(num, 200)

    def test_calculate_and_print_sum(self):
        # This function only prints, so we can only test for exceptions
        try:
            calculate_and_print_sum("test")
        except Exception as e:
            self.fail(f"calculate_and_print_sum() raised an exception {e}")

    def test_process_array(self):
        self.assertEqual(process_array([10, 60, 110, 160]), 0)
        self.assertEqual(process_array([50, 100, 150, 200]), -600)

    def test_loop_with_special_case(self):
        # This function only prints, so we can only test for exceptions
        try:
            loop_with_special_case()
        except Exception as e:
            self.fail(f"loop_with_special_case() raised an exception {e}")

    def test_read_file(self):
        # This function only prints, so we can only test for exceptions
        try:
            read_file()
        except Exception as e:
            self.fail(f"read_file() raised an exception {e}")

if __name__ == '__main__':
    unittest.main()
