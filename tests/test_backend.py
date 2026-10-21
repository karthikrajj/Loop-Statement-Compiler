"""
test_backend.py
===============
Comprehensive test suite for the C Loop Compiler Backend & Adapter.
Tests real compiler execution, demo mode fallback, error handling,
validation, and Flask API endpoints.
"""

import json
import os
import unittest
from compiler_adapter import CompilerAdapter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES_DIR = os.path.join(BASE_DIR, "examples")


def read_example(filename: str) -> str:
    path = os.path.join(EXAMPLES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestCompilerAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = CompilerAdapter()

    def test_status_detection(self):
        """Adapter correctly detects real compiler executable status."""
        status = self.adapter.get_status()
        self.assertIn("mode", status)
        self.assertIn(status["mode"], ["real", "demo"])
        self.assertIn("compiler_source_exists", status)
        self.assertTrue(status["compiler_source_exists"])

    def test_empty_source_validation(self):
        """Empty or whitespace-only code is rejected with validation error."""
        res = self.adapter.compile_source("")
        self.assertFalse(res["success"])
        self.assertEqual(res["mode"], "validation")
        self.assertTrue(len(res["errors"]) > 0)
        self.assertIn("empty", res["errors"][0]["message"].lower())

        res_spaces = self.adapter.compile_source("   \n\t  ")
        self.assertFalse(res_spaces["success"])

    def test_oversized_source_validation(self):
        """Inputs exceeding maximum size limit are rejected gracefully."""
        huge_code = "// " + "X" * (70 * 1024)
        res = self.adapter.compile_source(huge_code)
        self.assertFalse(res["success"])
        self.assertEqual(res["mode"], "validation")
        self.assertIn("size", res["errors"][0]["message"].lower())

    def test_valid_for_loop(self):
        """Valid for-loop compiles successfully with tokens and AST."""
        code = read_example("for_loop.c")
        res = self.adapter.compile_source(code)
        self.assertTrue(res["success"], f"Errors: {res.get('errors')}")
        self.assertGreater(len(res["tokens"]), 10)
        self.assertIn("for", res["ast"].lower())
        self.assertEqual(len(res["errors"]), 0)

    def test_valid_while_loop(self):
        """Valid while-loop compiles successfully."""
        code = read_example("while_loop.c")
        res = self.adapter.compile_source(code)
        self.assertTrue(res["success"], f"Errors: {res.get('errors')}")
        self.assertGreater(len(res["tokens"]), 10)
        self.assertIn("while", res["ast"].lower())
        self.assertEqual(len(res["errors"]), 0)

    def test_valid_do_while_loop(self):
        """Valid do-while loop compiles successfully."""
        code = read_example("do_while_loop.c")
        res = self.adapter.compile_source(code)
        self.assertTrue(res["success"], f"Errors: {res.get('errors')}")
        self.assertGreater(len(res["tokens"]), 10)
        self.assertIn("do-while", res["ast"].lower())
        self.assertEqual(len(res["errors"]), 0)

    def test_nested_loops(self):
        """Nested loops compile successfully."""
        code = read_example("nested_loops.c")
        res = self.adapter.compile_source(code)
        self.assertTrue(res["success"], f"Errors: {res.get('errors')}")
        self.assertIn("for", res["ast"].lower())
        self.assertIn("while", res["ast"].lower())

    def test_missing_semicolon(self):
        """Missing semicolon produces a syntax error."""
        code = read_example("missing_semicolon.c")
        res = self.adapter.compile_source(code)
        self.assertFalse(res["success"])
        self.assertGreater(len(res["errors"]), 0)
        has_semicolon_err = any("semicolon" in e["message"].lower() or "';'" in e["message"] for e in res["errors"])
        self.assertTrue(has_semicolon_err, f"Expected semicolon error, got: {res['errors']}")

    def test_mismatched_braces(self):
        """Mismatched braces produce a syntax error."""
        code = read_example("mismatched_braces.c")
        res = self.adapter.compile_source(code)
        self.assertFalse(res["success"])
        self.assertGreater(len(res["errors"]), 0)
        has_brace_err = any("brace" in e["message"].lower() or "'}'" in e["message"] for e in res["errors"])
        self.assertTrue(has_brace_err, f"Expected brace error, got: {res['errors']}")

    def test_invalid_condition(self):
        """Invalid condition produces syntax error."""
        code = read_example("invalid_condition.c")
        res = self.adapter.compile_source(code)
        self.assertFalse(res["success"])
        self.assertGreater(len(res["errors"]), 0)

    def test_demo_mode_fallback(self):
        """When pointed to a non-existent compiler dir, falls back to demo mode."""
        dummy_adapter = CompilerAdapter(compiler_dir=os.path.join(BASE_DIR, "non_existent_dir"))
        self.assertEqual(dummy_adapter.find_compiler_executable(), None)

        code = read_example("while_loop.c")
        res = dummy_adapter.compile_source(code)
        self.assertEqual(res["mode"], "demo")
        self.assertIn("DEMO MODE", res["message"])
        self.assertTrue(res["success"])
        self.assertGreater(len(res["tokens"]), 0)
        self.assertIn("while", res["ast"].lower())


class TestFlaskAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.flask_app = app.app
        cls.client = cls.flask_app.test_client()

    def test_get_status_api(self):
        """GET /api/status returns json status."""
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("mode", data)
        self.assertIn("real_compiler_available", data)

    def test_get_examples_api(self):
        """GET /api/examples returns list of available example programs."""
        resp = self.client.get("/api/examples")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("examples", data)
        self.assertGreaterEqual(len(data["examples"]), 6)

    def test_post_compile_valid(self):
        """POST /compile with valid code returns structured JSON."""
        code = read_example("for_loop.c")
        resp = self.client.post(
            "/compile",
            data=json.dumps({"source_code": code}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["tokens"], list)
        self.assertIsInstance(data["ast"], str)
        self.assertIsInstance(data["errors"], list)
        self.assertEqual(len(data["errors"]), 0)

    def test_post_compile_empty(self):
        """POST /compile with empty code returns 400 or validation error."""
        resp = self.client.post(
            "/compile",
            data=json.dumps({"source_code": ""}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 400])
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertGreater(len(data["errors"]), 0)


if __name__ == "__main__":
    unittest.main()
