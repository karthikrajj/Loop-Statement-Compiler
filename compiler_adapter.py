"""
compiler_adapter.py
===================
Adapter Layer for the C Loop Compiler.

Integrates the Python Flask backend with the native C compiler executable:
1. Discovers the native C compiler binary in the compiler/ directory.
2. Validates user input (source code presence, length limits).
3. Safely invokes the C compiler subprocess without shell=True, applying
   strict timeouts (5s) and safe temp files.
4. Captures stdout, stderr, and exit codes.
5. Parses structured JSON or text-based compiler outputs into a uniform JSON schema.
6. Clearly labels demo/simulated mode when the native compiler binary is absent,
   ensuring the application never claims simulated output is from a real compiler.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPILER_DIR = os.path.join(BASE_DIR, "compiler")
MAX_SOURCE_SIZE_BYTES = 64 * 1024  # 64 KB limit
DEFAULT_TIMEOUT_SECONDS = 5.0


class CompilerAdapter:
    """Manages integration with the external C compiler executable."""

    def __init__(self, compiler_dir: Optional[str] = None):
        self.compiler_dir = compiler_dir or COMPILER_DIR

    def find_compiler_executable(self) -> Optional[str]:
        """
        Locates the compiled C compiler binary.
        Checks:
        1. Environment variable LOOP_COMPILER_BIN
        2. compiler/compiler.exe (Windows)
        3. compiler/compiler (Linux/macOS)
        4. Other binaries in compiler/
        """
        env_bin = os.environ.get("LOOP_COMPILER_BIN")
        if env_bin and os.path.isfile(env_bin) and os.access(env_bin, os.X_OK):
            return env_bin

        candidate_names = [
            "compiler.exe",
            "compiler",
            "loop_compiler.exe",
            "loop_compiler",
            "c_compiler.exe",
            "c_compiler",
            "a.exe",
            "a.out",
        ]

        for name in candidate_names:
            path = os.path.join(self.compiler_dir, name)
            if os.path.isfile(path):
                # Check if compiler.c was updated more recently and needs recompilation
                source_path = os.path.join(self.compiler_dir, "compiler.c")
                if os.path.isfile(source_path):
                    try:
                        if os.path.getmtime(source_path) > os.path.getmtime(path):
                            self._compile_c_source(source_path, path)
                    except OSError:
                        pass
                return path

        # If binary doesn't exist yet, attempt to build from compiler.c
        source_path = os.path.join(self.compiler_dir, "compiler.c")
        if os.path.isfile(source_path):
            default_bin = os.path.join(self.compiler_dir, "compiler.exe" if os.name == "nt" else "compiler")
            if self._compile_c_source(source_path, default_bin):
                return default_bin

        return None

    def _compile_c_source(self, source_path: str, binary_path: str) -> bool:
        """Attempts to compile compiler.c into binary using available tools."""
        if not os.path.isfile(source_path):
            return False

        # Try build.bat on Windows
        if os.name == "nt":
            build_bat = os.path.join(self.compiler_dir, "build.bat")
            if os.path.isfile(build_bat):
                try:
                    res = subprocess.run([build_bat], cwd=self.compiler_dir, capture_output=True, text=True, timeout=20)
                    if res.returncode == 0 and os.path.isfile(binary_path):
                        return True
                except Exception:
                    pass

        # Try clang / gcc / cl directly
        bin_name = os.path.basename(binary_path)
        for comp in ["clang", "gcc", "cl"]:
            try:
                cmd = [comp, "-std=c99", "-Wall", "-O2", "compiler.c", "-o", bin_name] if comp != "cl" else ["cl", "/O2", "compiler.c", f"/Fe:{bin_name}"]
                res = subprocess.run(cmd, cwd=self.compiler_dir, capture_output=True, text=True, timeout=20)
                if res.returncode == 0 and os.path.isfile(binary_path):
                    return True
            except Exception:
                continue
        return False

    def get_status(self) -> Dict[str, Any]:
        """Returns the current state of compiler integration."""
        binary_path = self.find_compiler_executable()
        source_path = os.path.join(self.compiler_dir, "compiler.c")

        return {
            "mode": "real" if binary_path else "demo",
            "real_compiler_available": bool(binary_path),
            "compiler_binary": binary_path,
            "compiler_source_exists": os.path.isfile(source_path),
            "compiler_dir": self.compiler_dir,
            "timestamp": time.time(),
        }

    def compile_source(self, source_code: str) -> Dict[str, Any]:
        """
        Main entry point for compilation requests.
        Handles validation, routes to real compiler or demo fallback.
        """
        # Normalize source_code type defensively
        if isinstance(source_code, dict):
            source_code = source_code.get("value") or source_code.get("source_code") or ""
        elif not isinstance(source_code, str) and source_code is not None:
            source_code = str(source_code)

        # 1. Validation
        if source_code is None or not source_code.strip():
            return {
                "success": False,
                "mode": "validation",
                "tokens": [],
                "ast": "",
                "errors": [
                    {
                        "type": "ValidationError",
                        "message": "Source code cannot be empty. Please enter or load C source code.",
                        "line": 1,
                        "column": 1,
                    }
                ],
                "warnings": [],
                "message": "Input validation failed: source code is empty",
                "raw_stdout": "",
                "raw_stderr": "Validation error: empty source code",
                "exit_code": 1,
                "execution_time_ms": 0,
            }

        encoded_src = source_code.encode("utf-8")
        if len(encoded_src) > MAX_SOURCE_SIZE_BYTES:
            return {
                "success": False,
                "mode": "validation",
                "tokens": [],
                "ast": "",
                "errors": [
                    {
                        "type": "ValidationError",
                        "message": f"Source code exceeds maximum allowed size ({MAX_SOURCE_SIZE_BYTES // 1024} KB).",
                        "line": 1,
                        "column": 1,
                    }
                ],
                "warnings": [],
                "message": "Input validation failed: source code too large",
                "raw_stdout": "",
                "raw_stderr": "Validation error: payload too large",
                "exit_code": 1,
                "execution_time_ms": 0,
            }

        binary_path = self.find_compiler_executable()

        if binary_path:
            return self._execute_real_compiler(binary_path, source_code)
        else:
            return self._execute_demo_mode(source_code)

    def _execute_real_compiler(
        self, binary_path: str, source_code: str
    ) -> Dict[str, Any]:
        """
        Executes the real C compiler binary in a secure subprocess.
        """
        start_time = time.perf_counter()
        temp_dir = tempfile.mkdtemp(prefix="loop_compiler_")
        temp_src_path = os.path.join(temp_dir, "input.c")

        try:
            with open(temp_src_path, "w", encoding="utf-8") as f:
                f.write(source_code)

            # Ensure source code passed to C executable through standard input with END on its own line
            clean_code = source_code.rstrip()
            stdin_payload = f"{clean_code}\nEND\n"

            # Execute the compiler binary passing source via standard input
            cmd = [binary_path]
            process = subprocess.run(
                cmd,
                input=stdin_payload,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TIMEOUT_SECONDS,
                cwd=self.compiler_dir,
            )

            # If binary expects file argument and produced no output, fallback with file path
            if not process.stdout and not process.stderr and process.returncode != 0:
                cmd = [binary_path, temp_src_path]
                process = subprocess.run(
                    cmd,
                    input=stdin_payload,
                    capture_output=True,
                    text=True,
                    timeout=DEFAULT_TIMEOUT_SECONDS,
                    cwd=self.compiler_dir,
                )

            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            stdout = process.stdout or ""
            stderr = process.stderr or ""
            exit_code = process.returncode

            # Attempt to parse stdout as JSON or structured/unstructured compiler output
            parsed_data = self._parse_compiler_output(stdout, stderr, exit_code)
            parsed_data["mode"] = "real"
            parsed_data["raw_stdout"] = stdout
            parsed_data["raw_stderr"] = stderr
            parsed_data["exit_code"] = exit_code
            parsed_data["execution_time_ms"] = execution_time_ms
            parsed_data["compiler_binary"] = binary_path

            return parsed_data

        except subprocess.TimeoutExpired:
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "mode": "real",
                "tokens": [],
                "ast": "",
                "errors": [
                    {
                        "type": "ExecutionTimeout",
                        "message": f"Compilation timed out after {DEFAULT_TIMEOUT_SECONDS} seconds.",
                        "line": 0,
                        "column": 0,
                    }
                ],
                "warnings": [],
                "message": "Compilation timed out",
                "raw_stdout": "",
                "raw_stderr": f"Subprocess timed out after {DEFAULT_TIMEOUT_SECONDS}s",
                "exit_code": -1,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "mode": "real",
                "tokens": [],
                "ast": "",
                "errors": [
                    {
                        "type": "BackendError",
                        "message": f"Failed to execute compiler binary: {str(e)}",
                        "line": 0,
                        "column": 0,
                    }
                ],
                "warnings": [],
                "message": f"Subprocess execution error: {str(e)}",
                "raw_stdout": "",
                "raw_stderr": str(e),
                "exit_code": -1,
                "execution_time_ms": execution_time_ms,
            }

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _parse_compiler_output(
        self, stdout: str, stderr: str, exit_code: int
    ) -> Dict[str, Any]:
        """
        Parses compiler output. Supports JSON output, Member 1 loop compiler format,
        formatted sections, or unstructured text output without fabricating data.
        """
        clean_stdout = stdout.strip()

        # Try JSON parsing
        if clean_stdout.startswith("{") and clean_stdout.endswith("}"):
            try:
                data = json.loads(clean_stdout)
                return {
                    "success": bool(data.get("success", exit_code == 0)),
                    "tokens": data.get("tokens", []),
                    "ast": data.get("ast", ""),
                    "errors": data.get("errors", []),
                    "warnings": data.get("warnings", []),
                    "message": data.get(
                        "message",
                        "Compilation completed successfully"
                        if exit_code == 0
                        else "Compilation failed",
                    ),
                }
            except json.JSONDecodeError:
                pass

        # Text-based parsing fallback
        tokens = []
        ast_lines = []
        errors = []
        warnings = []
        general_output_lines = []

        in_tokens = False
        in_ast = False
        in_diagnostics = False

        # Member 1 specific patterns: [ERROR]: ...
        member1_err_re = re.compile(r"\[ERROR\]:\s*(.*)", re.IGNORECASE)
        has_member1_success = "[SUCCESS]" in stdout
        has_member1_failure = "[FAILURE]" in stdout

        angle_token_re = re.compile(
            r'<\s*([A-Za-z_]+)\s*,\s*"((?:\\.|[^"\\])*)"\s*(?:,\s*(\d+))?\s*(?:,\s*(\d+))?\s*>|'
            r'<\s*([A-Za-z_]+)\s*,\s*\"?([^\",>]+)\"?\s*(?:,\s*(\d+))?\s*(?:,\s*(\d+))?\s*>',
            re.IGNORECASE
        )
        labeled_token_re = re.compile(r"Token:\s*([A-Za-z_]+)\s*[,|]\s*(?:Lexeme:\s*)?\"?([^\",|\n]+)\"?\s*(?:[,|]\s*(?:Line:\s*)?(\d+))?", re.IGNORECASE)
        diag_re = re.compile(r"\[(.*?)\].*?Line\s+(\d+)(?:.*?Col\s+(\d+))?\s*:\s*(.*)", re.IGNORECASE)
        gcc_error_re = re.compile(r"(?:[A-Za-z0-9_.\-\\]+\.c):(\d+):(?:(\d+):)?\s*(error|warning|fatal error)?\s*:\s*(.*)", re.IGNORECASE)
        line_error_re = re.compile(r"(?:Line\s+(\d+)|Error\s+at\s+line\s+(\d+))\s*:\s*(.*)", re.IGNORECASE)

        for line in stdout.splitlines():
            line_str = line.strip()
            if not line_str:
                if in_ast:
                    ast_lines.append(line)
                continue

            # Check Member 1 error format: [ERROR]: message
            m1_err = member1_err_re.match(line_str)
            if m1_err:
                err_text = m1_err.group(1).strip()
                line_match = re.search(r"line\s+(\d+)", err_text, re.IGNORECASE)
                line_no = int(line_match.group(1)) if line_match else 1
                errors.append({
                    "type": "SyntaxError" if ("brace" in err_text.lower() or ";" in err_text or "closing" in err_text.lower()) else "SemanticError",
                    "message": err_text,
                    "line": line_no,
                    "column": 1
                })
                continue

            # Detect PARSE TREE section
            if "PARSE TREE" in line_str:
                in_tokens = False
                in_ast = True
                in_diagnostics = False
                continue

            # Detect other section markers
            if "=== TOKENS" in line_str:
                in_tokens = True
                in_ast = False
                in_diagnostics = False
                continue
            elif "=== ABSTRACT SYNTAX TREE" in line_str or "=== AST" in line_str:
                in_tokens = False
                in_ast = True
                in_diagnostics = False
                continue
            elif "=== DIAGNOSTICS" in line_str or "=== ERRORS" in line_str or "=== WARNINGS" in line_str:
                in_tokens = False
                in_ast = False
                in_diagnostics = True
                continue

            # Inside tokens section
            if in_tokens:
                if line_str.startswith("====") or line_str.startswith("--- COMPILATION") or "PARSE TREE" in line_str:
                    in_tokens = False
                    if "PARSE TREE" in line_str:
                        in_ast = True
                    continue
                if not line_str.startswith("---") and not line_str.startswith("TYPE"):
                    tok_m = angle_token_re.match(line_str)
                    if tok_m:
                        groups = tok_m.groups()
                        if groups[0] is not None:
                            t_type, t_lex, t_line, t_col = groups[0], groups[1], groups[2], groups[3]
                        else:
                            t_type, t_lex, t_line, t_col = groups[4], groups[5], groups[6], groups[7]
                        tokens.append({
                            "type": t_type,
                            "lexeme": t_lex,
                            "line": int(t_line) if t_line else 1,
                            "column": int(t_col) if t_col else 1,
                        })
                    else:
                        parts = line_str.split(None, 3)
                        if len(parts) >= 2:
                            t_type = parts[0]
                            t_lex = parts[1]
                            t_line = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 1
                            t_col = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 1
                            tokens.append({"type": t_type, "lexeme": t_lex, "line": t_line, "column": t_col})
                continue

            # Inside AST / PARSE TREE section
            if in_ast:
                if line_str.startswith("----") or line_str.startswith("====") or line_str.startswith("--- COMPILATION"):
                    if ast_lines:
                        in_ast = False
                    continue
                ast_lines.append(line)
                continue

            # Inside diagnostics section
            if in_diagnostics:
                diag_match = diag_re.match(line_str)
                if diag_match:
                    d_type, d_line, d_col, d_msg = diag_match.groups()
                    item = {"type": d_type, "message": d_msg, "line": int(d_line), "column": int(d_col) if d_col else 1}
                    if "warning" in d_type.lower():
                        warnings.append(item)
                    else:
                        errors.append(item)
                else:
                    errors.append({"type": "SyntaxError", "message": line_str, "line": 1, "column": 1})
                continue

            # Filter interactive terminal prompt banners from general output
            if any(banner in line_str for banner in ["LOOP COMPILER", "Enter code (type 'END'", "--- COMPILATION LOG ---", "[SUCCESS]", "[FAILURE]"]):
                continue
            if line_str.startswith("====") or line_str.startswith("----"):
                continue

            # Unsectioned line-by-line checks
            tok_m = angle_token_re.match(line_str)
            if tok_m:
                groups = tok_m.groups()
                if groups[0] is not None:
                    t_type, t_lex, t_line, t_col = groups[0], groups[1], groups[2], groups[3]
                else:
                    t_type, t_lex, t_line, t_col = groups[4], groups[5], groups[6], groups[7]
                tokens.append({
                    "type": t_type,
                    "lexeme": t_lex,
                    "line": int(t_line) if t_line else 1,
                    "column": int(t_col) if t_col else 1,
                })
                continue
            labeled_m = labeled_token_re.match(line_str)
            if labeled_m:
                t_type, t_lex, t_line = labeled_m.groups()[:3]
                tokens.append({
                    "type": t_type,
                    "lexeme": t_lex,
                    "line": int(t_line) if t_line else 1,
                    "column": 1,
                })
                continue

            gcc_m = gcc_error_re.match(line_str)
            if gcc_m:
                e_line, e_col, e_sev, e_msg = gcc_m.groups()
                item = {
                    "type": "SemanticWarning" if e_sev and "warning" in e_sev.lower() else "SyntaxError",
                    "message": e_msg.strip(),
                    "line": int(e_line) if e_line else 1,
                    "column": int(e_col) if e_col else 1,
                }
                if item["type"] == "SemanticWarning":
                    warnings.append(item)
                else:
                    errors.append(item)
                continue

            line_err_m = line_error_re.match(line_str)
            if line_err_m:
                l1, l2, e_msg = line_err_m.groups()
                errors.append({"type": "SyntaxError", "message": e_msg.strip(), "line": int(l1 or l2 or 1), "column": 1})
                continue

            general_output_lines.append(line)

        # Check stderr for additional error messages
        if stderr.strip():
            for s_line in stderr.splitlines():
                s_str = s_line.strip()
                if not s_str:
                    continue
                gcc_m = gcc_error_re.match(s_str)
                if gcc_m:
                    e_line, e_col, e_sev, e_msg = gcc_m.groups()
                    item = {
                        "type": "SemanticWarning" if e_sev and "warning" in e_sev.lower() else "SyntaxError",
                        "message": e_msg.strip(),
                        "line": int(e_line) if e_line else 1,
                        "column": int(e_col) if e_col else 1,
                    }
                    if item["type"] == "SemanticWarning":
                        warnings.append(item)
                    else:
                        errors.append(item)
                else:
                    line_err_m = line_error_re.match(s_str)
                    if line_err_m:
                        l1, l2, e_msg = line_err_m.groups()
                        errors.append({"type": "SyntaxError", "message": e_msg.strip(), "line": int(l1 or l2 or 1), "column": 1})
                    elif exit_code != 0:
                        errors.append({"type": "CompilerError", "message": s_str, "line": 1, "column": 1})

        # Ensure compilation failures and runtime errors are reported clearly rather than showing a false success
        if has_member1_failure or len(errors) > 0 or exit_code != 0:
            is_success = False
        elif has_member1_success:
            is_success = True
        else:
            is_success = (exit_code == 0 and len(errors) == 0)

        # Clean AST output
        final_ast = "\n".join(ast_lines).strip() if ast_lines else ""
        if not final_ast and general_output_lines and is_success:
            final_ast = "\n".join(general_output_lines).strip()

        # Compilation message
        if is_success:
            message = "Code is Syntactically & Semantically Valid!"
        else:
            err_count = len(errors)
            message = f"Compilation failed with {err_count} error{'s' if err_count != 1 else ''}. Parse tree suppressed."

        return {
            "success": is_success,
            "tokens": tokens,
            "ast": final_ast,
            "errors": errors,
            "warnings": warnings,
            "message": message,
        }

    def _execute_demo_mode(self, source_code: str) -> Dict[str, Any]:
        """
        Demo / Simulated Mode.
        Clearly labeled simulation used when the native compiler executable
        has not been compiled yet. Provides full loop analysis for testing.
        """
        start_time = time.perf_counter()
        analyzer = _DemoCompilerAnalyzer(source_code)
        result = analyzer.analyze()
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        result["mode"] = "demo"
        result["execution_time_ms"] = execution_time_ms
        result["compiler_binary"] = None
        result["raw_stdout"] = (
            "[DEMO MODE SIMULATION]\n"
            "Notice: Native C compiler binary was not found in 'compiler/compiler.exe'.\n"
            "To connect the real C compiler:\n"
            "  1. Navigate to compiler/\n"
            "  2. Run 'build.bat' (or 'gcc -std=c99 compiler.c -o compiler.exe')\n"
            "  3. Refresh or click Compile to use the real native binary.\n"
        )
        result["raw_stderr"] = ""
        result["exit_code"] = 0 if result["success"] else 1
        return result


class _DemoCompilerAnalyzer:
    """Internal demo analyzer providing realistic tokens, AST, and error checks."""

    KEYWORDS = {
        "for", "while", "do", "if", "else", "int", "float", "double", "char",
        "void", "return", "break", "continue", "switch", "case", "default"
    }

    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def analyze(self) -> Dict[str, Any]:
        self._tokenize()
        ast_str = self._parse_and_generate_ast()
        success = len(self.errors) == 0

        demo_badge_message = (
            "⚠️ DEMO MODE: Showing simulated analysis (compiler binary not yet built). "
            + ("No syntax errors found." if success else f"Found {len(self.errors)} syntax error(s).")
        )

        return {
            "success": success,
            "tokens": self.tokens,
            "ast": ast_str,
            "errors": self.errors,
            "warnings": self.warnings,
            "message": demo_badge_message,
        }

    def _tokenize(self):
        src = self.source
        lines = src.split("\n")

        for line_num, line in enumerate(lines, start=1):
            col = 1
            i = 0
            while i < len(line):
                c = line[i]

                if c.isspace():
                    col += 1
                    i += 1
                    continue

                if c == "#":
                    # Preprocessor
                    rest = line[i:].strip()
                    self.tokens.append({"type": "PREPROCESSOR", "lexeme": rest, "line": line_num, "column": col})
                    break

                if line[i:i + 2] == "//":
                    # Comment
                    break

                # String literal
                if c == '"':
                    start_col = col
                    str_val = [c]
                    i += 1
                    col += 1
                    closed = False
                    while i < len(line):
                        sc = line[i]
                        str_val.append(sc)
                        col += 1
                        i += 1
                        if sc == '"' and (len(str_val) < 2 or str_val[-2] != '\\'):
                            closed = True
                            break
                    lexeme = "".join(str_val)
                    if not closed:
                        self.errors.append({"type": "LexicalError", "message": "Unterminated string literal", "line": line_num, "column": start_col})
                    self.tokens.append({"type": "STRING", "lexeme": lexeme, "line": line_num, "column": start_col})
                    continue

                # Identifier or Keyword
                if c.isalpha() or c == "_":
                    start_col = col
                    ident = []
                    while i < len(line) and (line[i].isalnum() or line[i] == "_"):
                        ident.append(line[i])
                        i += 1
                        col += 1
                    lexeme = "".join(ident)
                    tok_type = "KEYWORD" if lexeme in self.KEYWORDS else "IDENTIFIER"
                    self.tokens.append({"type": tok_type, "lexeme": lexeme, "line": line_num, "column": start_col})
                    continue

                # Number
                if c.isdigit():
                    start_col = col
                    num = []
                    while i < len(line) and (line[i].isdigit() or line[i] == "."):
                        num.append(line[i])
                        i += 1
                        col += 1
                    self.tokens.append({"type": "NUMBER", "lexeme": "".join(num), "line": line_num, "column": start_col})
                    continue

                # Multi-char operators
                two_char = line[i:i + 2]
                if two_char in ["++", "--", "+=", "-=", "*=", "/=", "%=", "==", "!=", "<=", ">=", "&&", "||"]:
                    self.tokens.append({"type": "OPERATOR", "lexeme": two_char, "line": line_num, "column": col})
                    i += 2
                    col += 2
                    continue

                # Single-char operators
                if c in "+-*/%=<>!&|^~?":
                    self.tokens.append({"type": "OPERATOR", "lexeme": c, "line": line_num, "column": col})
                    i += 1
                    col += 1
                    continue

                # Delimiters
                if c in ";,(){}[]:":
                    self.tokens.append({"type": "DELIMITER", "lexeme": c, "line": line_num, "column": col})
                    i += 1
                    col += 1
                    continue

                # Unrecognized
                self.errors.append({"type": "LexicalError", "message": f"Unrecognized character '{c}'", "line": line_num, "column": col})
                i += 1
                col += 1

    def _parse_and_generate_ast(self) -> str:
        # Check mismatched braces
        brace_stack = []
        for tok in self.tokens:
            if tok["lexeme"] == "{":
                brace_stack.append(tok)
            elif tok["lexeme"] == "}":
                if brace_stack:
                    brace_stack.pop()
                else:
                    self.errors.append({"type": "SyntaxError", "message": "Unexpected closing brace '}' without matching opening '{'", "line": tok["line"], "column": tok["column"]})

        for unclosed in brace_stack:
            self.errors.append({
                "type": "SyntaxError",
                "message": f"Mismatched braces: Missing closing '}}' for block opened at line {unclosed['line']}",
                "line": unclosed["line"],
                "column": unclosed["column"]
            })

        # Check for missing semicolon after declaration / expressions
        for idx in range(len(self.tokens) - 1):
            curr = self.tokens[idx]
            nxt = self.tokens[idx + 1]

            # e.g., int i = 0 followed directly by while/return/int without semicolon
            if curr["type"] in ("NUMBER", "IDENTIFIER") and nxt["lexeme"] in ("while", "for", "do", "return", "int", "float", "char"):
                # Check if semicolon is missing
                # If they are on different lines or same line without ';'
                prev_tokens = [t["lexeme"] for t in self.tokens[max(0, idx - 5):idx + 1]]
                if "=" in prev_tokens and ";" not in prev_tokens:
                    self.errors.append({
                        "type": "SyntaxError",
                        "message": f"Expected ';' before '{nxt['lexeme']}'",
                        "line": curr["line"],
                        "column": curr["column"] + len(curr["lexeme"])
                    })

        # Check loop condition syntax
        for idx, tok in enumerate(self.tokens):
            if tok["lexeme"] in ("while", "for"):
                if idx + 1 < len(self.tokens) and self.tokens[idx + 1]["lexeme"] == "(":
                    # Find matching ')'
                    paren_depth = 1
                    p_idx = idx + 2
                    cond_tokens = []
                    while p_idx < len(self.tokens) and paren_depth > 0:
                        ptok = self.tokens[p_idx]
                        if ptok["lexeme"] == "(":
                            paren_depth += 1
                        elif ptok["lexeme"] == ")":
                            paren_depth -= 1
                            if paren_depth == 0:
                                break
                        cond_tokens.append(ptok)
                        p_idx += 1

                    if paren_depth > 0:
                        self.errors.append({
                            "type": "SyntaxError",
                            "message": f"Missing closing ')' for {tok['lexeme']} condition",
                            "line": tok["line"],
                            "column": tok["column"]
                        })

                    # Check for invalid condition like (i < )
                    if tok["lexeme"] == "while":
                        if not cond_tokens:
                            self.errors.append({
                                "type": "SyntaxError",
                                "message": "Empty condition in while loop",
                                "line": tok["line"],
                                "column": tok["column"]
                            })
                        else:
                            last_tok = cond_tokens[-1]
                            if last_tok["type"] == "OPERATOR" and last_tok["lexeme"] in ("<", ">", "<=", ">=", "==", "!=", "&&", "||"):
                                self.errors.append({
                                    "type": "SyntaxError",
                                    "message": f"Invalid loop condition: trailing operator '{last_tok['lexeme']}' with missing right-hand operand",
                                    "line": last_tok["line"],
                                    "column": last_tok["column"]
                                })

                            # Semantic warning for assignment '='
                            for ctok in cond_tokens:
                                if ctok["lexeme"] == "=":
                                    self.warnings.append({
                                        "type": "SemanticWarning",
                                        "message": "Assignment '=' used in loop condition; did you mean '=='?",
                                        "line": ctok["line"],
                                        "column": ctok["column"]
                                    })

        # Generate readable AST
        ast_lines = ["TranslationUnit"]
        indent = "  "

        has_main = any(t["lexeme"] == "main" for t in self.tokens)
        if has_main:
            ast_lines.append(f"{indent}|- Function: main (int)")
            indent = "    "
            ast_lines.append(f"{indent}|- CompoundStmt")
            indent = "      "

        # Walk through tokens to construct loops
        i = 0
        while i < len(self.tokens):
            t = self.tokens[i]

            if t["lexeme"] == "for":
                ast_lines.append(f"{indent}|- ForLoop")
                ast_lines.append(f"{indent}  |- InitClause")
                ast_lines.append(f"{indent}  |- ConditionClause")
                ast_lines.append(f"{indent}  |- UpdateClause")
                ast_lines.append(f"{indent}  |- Body: CompoundStmt")
            elif t["lexeme"] == "while":
                # Check if preceding was do
                is_do_while = (i > 0 and any(self.tokens[j]["lexeme"] == "do" for j in range(max(0, i - 15), i)))
                if not is_do_while:
                    ast_lines.append(f"{indent}|- WhileLoop")
                    ast_lines.append(f"{indent}  |- Condition")
                    ast_lines.append(f"{indent}  |- Body: CompoundStmt")
            elif t["lexeme"] == "do":
                ast_lines.append(f"{indent}|- DoWhileLoop")
                ast_lines.append(f"{indent}  |- Body: CompoundStmt")
                ast_lines.append(f"{indent}  |- Condition")
            elif t["lexeme"] in ("int", "float", "char") and i + 1 < len(self.tokens) and self.tokens[i + 1]["type"] == "IDENTIFIER" and self.tokens[i + 1]["lexeme"] != "main":
                var_name = self.tokens[i + 1]["lexeme"]
                ast_lines.append(f"{indent}|- VarDecl: {t['lexeme']} {var_name}")
            elif t["lexeme"] == "return":
                ast_lines.append(f"{indent}|- ReturnStmt")
            i += 1

        if len(ast_lines) == 1:
            ast_lines.append("  |- EmptyProgram")

        return "\n".join(ast_lines)
