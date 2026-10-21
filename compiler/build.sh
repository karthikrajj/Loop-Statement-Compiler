#!/bin/bash
set -e

echo "=============================================="
echo "Building C Loop Compiler"
echo "=============================================="

if command -v clang &> /dev/null; then
    echo "Compiling with clang..."
    clang -std=c99 -Wall -Wextra -O2 compiler.c -o compiler
elif command -v gcc &> /dev/null; then
    echo "Compiling with gcc..."
    gcc -std=c99 -Wall -Wextra -O2 compiler.c -o compiler
else
    echo "ERROR: Neither clang nor gcc found on PATH."
    exit 1
fi

if [ -f "./compiler" ]; then
    chmod +x ./compiler
    echo "[SUCCESS] compiler binary built successfully!"
else
    echo "[FAILED] Compilation failed."
    exit 1
fi
