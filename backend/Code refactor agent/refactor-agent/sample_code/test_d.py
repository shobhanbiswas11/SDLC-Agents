import unittest
from sample_code.d import calculate_total, generate_random_list, process_list, recursive_sum, modify_counter, execute_weird_loop

class TestDModule(unittest.TestCase):

    def test_calculate_total(self):
        self.assertEqual(calculate_total(1, 1), 0)
        self.assertEqual(calculate_total(2, 2), 1)
        self.assertEqual(calculate_total(3, 3), 9)

    def test_generate_random_list(self):
        result = generate_random_list()
        self.assertEqual(len(result), 40)
        for num in result:
            self.assertGreaterEqual(num, 1)
            self.assertLessEqual(num, 100)

    def test_process_list(self):
        self.assertEqual(process_list([1, 2, 3, 4]), 2)
        self.assertEqual(process_list([2, 2, 2, 2]), 8)
        self.assertEqual(process_list([1, 1, 1, 1]), -4)

    def test_recursive_sum(self):
        self.assertEqual(recursive_sum(0), 0)
        self.assertEqual(recursive_sum(1), 1)
        self.assertEqual(recursive_sum(5), 15)

    def test_modify_counter(self):
        global COUNTER
        COUNTER = 0
        modify_counter()
        self.assertGreaterEqual(COUNTER, 10)
        self.assertLessEqual(COUNTER, 50)

    def test_execute_weird_loop(self):
        # This test is more about ensuring no exceptions are raised
        try:
            execute_weird_loop()
        except Exception as e:
            self.fail(f"execute_weird_loop() raised an exception {e}")

if __name__ == '__main__':
    unittest.main()
