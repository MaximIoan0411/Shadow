"""Run every security test, with throwaway keys: a clean clone needs no setup and the real keys are never touched.

    python security/run_tests.py

Exit code 0 only if every test script passed.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

with tempfile.TemporaryDirectory() as keys_dir:
    env = {**os.environ, "SHADOW_KEYS_DIR": keys_dir}
    subprocess.run([sys.executable, str(HERE / "keys" / "generate_keys.py")], env=env, check=True, capture_output=True)

    failed = []
    for test in sorted(HERE.glob("*/test_*.py")):
        name = str(test.relative_to(HERE))
        print("\n===", name)
        result = subprocess.run([sys.executable, test.name], cwd=test.parent, env=env)
        if result.returncode != 0:
            failed.append(name)

print()
if failed:
    sys.exit("FAILED: " + ", ".join(failed))
print("All security tests passed.")
