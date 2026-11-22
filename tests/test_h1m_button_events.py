"""Regression tests for H1M wall switch button event configuration."""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "custom_components/aqara_gateway/core/utils.py"


class H1MButtonEventTests(unittest.TestCase):
    """Validate the H1M button reports are exposed as event parameters."""

    @classmethod
    def setUpClass(cls):
        module = ast.parse(SOURCE.read_text(encoding="utf-8"))
        devices_node = next(
            node
            for node in module.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "DEVICES_AIOT"
                for target in node.targets
            )
        )
        devices = ast.literal_eval(devices_node.value)
        cls.h1m = next(
            device
            for device in devices
            if "lumi.switch.acn031" in device
        )

    def test_button_reports_are_event_parameters(self):
        """H1M button reports should create Home Assistant event entities."""
        expected = {
            "button_1": "event",
            "button_2": "event",
            "button_3": "event",
            "button_both_12": "event",
            "button_both_13": "event",
            "button_both_23": "event",
        }
        actual = {
            param[2]: param[3]
            for param in self.h1m["params"]
            if param[2] in expected
        }
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
