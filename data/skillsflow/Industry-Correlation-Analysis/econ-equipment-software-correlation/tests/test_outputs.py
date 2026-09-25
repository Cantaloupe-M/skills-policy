"""
Test suite for Task 2 (dividend, parameter-only): equipment-software correlation.
"""

import os
import unittest

EXPECTED = 0.59552


class TestEquipmentSoftwareCorrelation(unittest.TestCase):
    def get_answer_path(self):
        for path in ["/root/answer.txt", "answer.txt"]:
            if os.path.exists(path):
                return path
        return None

    def test_answer_exists(self):
        self.assertIsNotNone(self.get_answer_path(), "Expected answer.txt to exist")

    def test_answer_format(self):
        path = self.get_answer_path()
        if path is None:
            self.skipTest("answer.txt missing")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        self.assertRegex(content, r"^-?\d+\.?\d*$", "Answer must be a valid number")

    def test_answer_value(self):
        path = self.get_answer_path()
        if path is None:
            self.skipTest("answer.txt missing")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        value = float(content)
        self.assertAlmostEqual(value, EXPECTED, delta=0.001)


if __name__ == "__main__":
    unittest.main(verbosity=2)
