import importlib.util
from pathlib import Path
import unittest


class AcceptanceScenarios(unittest.TestCase):
    def test_fictional_workflows_preserve_capacity_and_state(self):
        path = Path(__file__).resolve().parents[1] / "tools" / "evaluate.py"
        spec = importlib.util.spec_from_file_location("scenario_eval", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        evidence = module.run_scenarios()
        self.assertEqual(len(evidence["results"]), 4)
        self.assertTrue(all(result["status"] == "passed" for result in evidence["results"]))


if __name__ == "__main__":
    unittest.main()
