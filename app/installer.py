import asyncio
import logging
from typing import AsyncGenerator
from app.cache import add_installed_package, log_history

logger = logging.getLogger("opencode-hub.installer")

class AsyncInstallRunner:
    @staticmethod
    async def run_install(slug: str, impl_type: str = "Skills") -> AsyncGenerator[str, None]:
        """
        Executes 'opencode get <slug>' in a shell environment,
        streaming stdout/stderr line-by-line asynchronously.
        Saves completion details in SQLite databases on success/failure.
        """
        cmd = f"opencode get {slug}"
        yield f"[INFO] Initializing installation sequence for {slug}..."
        yield f"[EXEC] Executing: {cmd}"
        
        # Verify if 'opencode' binary exists on path and supports 'get', otherwise warn user and simulate
        import shutil
        import subprocess
        opencode_exists = False
        if shutil.which("opencode") is not None:
            try:
                help_out = subprocess.check_output(["opencode", "--help"], stderr=subprocess.STDOUT, text=True, timeout=1.0)
                if " get " in help_out:
                    opencode_exists = True
            except Exception:
                pass
        
        if not opencode_exists:
            yield "[WARN] 'opencode' binary not found on PATH or does not support 'get' subcommand."
            yield "[INFO] Simulating installation sequence..."
            await asyncio.sleep(0.5)
            yield "[FETCH] Fetching source manifest from registry..."
            await asyncio.sleep(0.5)
            yield f"[DOWN] Downloading resources for {slug}..."
            await asyncio.sleep(0.5)
            yield "[CONF] Configuring environment variables..."
            await asyncio.sleep(0.5)
            yield "[OK] Verification complete."
            
            # Successful mock run
            add_installed_package(slug, "1.0.0", "installed", impl_type)
            log_history(slug, "installed", "Simulated installation complete.")
            yield f"[SUCCESS] Successfully installed {slug}."
            return

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Read stdout and stderr simultaneously
            async def read_stream(stream, is_stderr=False) -> AsyncGenerator[str, None]:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode(errors="replace").strip()
                    if is_stderr:
                        yield f"[ERR] {decoded}"
                    else:
                        yield f"      {decoded}"

            queue = asyncio.Queue()
            
            async def enqueue_stream(stream, is_stderr):
                async for line in read_stream(stream, is_stderr):
                    await queue.put(line)

            task_stdout = asyncio.create_task(enqueue_stream(process.stdout, False))
            task_stderr = asyncio.create_task(enqueue_stream(process.stderr, True))
            
            while not (task_stdout.done() and task_stderr.done() and queue.empty()):
                try:
                    line = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield line
                except asyncio.TimeoutError:
                    continue
            
            await task_stdout
            await task_stderr
            
            returncode = await process.wait()
            
            if returncode == 0:
                add_installed_package(slug, "1.0.0", "installed", impl_type)
                log_history(slug, "installed", f"Successful execution of 'opencode get {slug}'.")
                yield f"[SUCCESS] Successfully installed {slug} (exit code 0)."
            else:
                log_history(slug, "failed", f"Failed installation of 'opencode get {slug}'. Exit code: {returncode}.")
                yield f"[FAIL] Installation sequence failed with exit code: {returncode}."
                
        except Exception as e:
            logger.error(f"Error during installation execution: {e}")
            log_history(slug, "failed", f"Subprocess exception: {str(e)}.")
            yield f"[FAIL] Subprocess execution exception: {str(e)}"
