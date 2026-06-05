from __future__ import annotations

import importlib.util
import py_compile
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_FILE = ROOT / "pipeline_core.py"
PROMPTS_DIR = ROOT / "prompts"


def load_pipeline_core():
    if "requests" not in sys.modules:
        requests_stub = types.ModuleType("requests")
        requests_stub.RequestException = Exception
        sys.modules["requests"] = requests_stub

    spec = importlib.util.spec_from_file_location("pipeline_core_test", CORE_FILE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {CORE_FILE}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PipelineCoreTests(unittest.TestCase):
    def test_pipeline_core_compiles(self) -> None:
        py_compile.compile(str(CORE_FILE), doraise=True)

    def test_default_prompts_load_from_text_files(self) -> None:
        module = load_pipeline_core()
        cfg = module.MultiAgentConfig()

        self.assertEqual(
            cfg.system_planner,
            (PROMPTS_DIR / "system_planner.txt").read_text(encoding="utf-8").strip(),
        )
        self.assertEqual(
            cfg.system_coder,
            (PROMPTS_DIR / "system_coder.txt").read_text(encoding="utf-8").strip(),
        )
        self.assertEqual(
            cfg.system_reviewer,
            (PROMPTS_DIR / "system_reviewer.txt").read_text(encoding="utf-8").strip(),
        )


if __name__ == "__main__":
    unittest.main()
