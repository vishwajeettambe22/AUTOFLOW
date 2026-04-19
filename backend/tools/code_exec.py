import asyncio
import subprocess
import tempfile
import os
import structlog

from core.config import settings

log = structlog.get_logger()

ALLOWED_LANGUAGES = {"python", "bash"}
BLOCKED_IMPORTS = ["os.system", "subprocess", "shutil.rmtree", "__import__('os')"]


def _is_safe(code: str) -> tuple[bool, str]:
    """Basic static check before execution."""
    lowered = code.lower()
    dangerous = ["rm -rf", "os.system", "shutil.rmtree", "import subprocess"]
    for d in dangerous:
        if d in lowered:
            return False, f"Blocked: contains '{d}'"
    return True, ""


async def execute_code(code: str, language: str = "python") -> dict:
    """
    Execute code in a subprocess with timeout.
    Returns: {success, stdout, stderr, exit_code}
    """
    if language not in ALLOWED_LANGUAGES:
        return {"success": False, "stdout": "", "stderr": f"Language '{language}' not allowed", "exit_code": -1}

    safe, reason = _is_safe(code)
    if not safe:
        return {"success": False, "stdout": "", "stderr": reason, "exit_code": -1}

    suffix = ".py" if language == "python" else ".sh"

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(code)
            tmp_path = f.name

        cmd = ["python3", tmp_path] if language == "python" else ["bash", tmp_path]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=settings.CODE_EXEC_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {settings.CODE_EXEC_TIMEOUT}s",
                "exit_code": -1,
            }

        stdout_str = stdout.decode()[:settings.CODE_EXEC_MAX_OUTPUT]
        stderr_str = stderr.decode()[:1024]

        return {
            "success": proc.returncode == 0,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "exit_code": proc.returncode,
        }

    except Exception as e:
        log.error("code_exec_error", error=str(e))
        return {"success": False, "stdout": "", "stderr": str(e), "exit_code": -1}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
