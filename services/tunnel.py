"""
Cloudflare Quick Tunnel management module.
Provides public HTTPS access to the local FastAPI port (8000) via cloudflared or localtunnel.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger("kai_assistant.tunnel")

_active_tunnel_url: Optional[str] = None


def get_current_tunnel_url() -> Optional[str]:
    """Retrieve the currently active public HTTPS tunnel URL."""
    return _active_tunnel_url


def set_current_tunnel_url(url: Optional[str]) -> None:
    """Set the currently active public HTTPS tunnel URL."""
    global _active_tunnel_url
    _active_tunnel_url = url


class TunnelService:

    """Manages cloudflared / localtunnel process lifecycle and URL discovery."""

    def __init__(self, port: int = 8000, cloudflared_path: Optional[str] = None):
        self.port = port
        self.cloudflared_path = cloudflared_path or self._resolve_cloudflared()
        self.process: Optional[asyncio.subprocess.Process] = None
        self.public_url: Optional[str] = None
        self._reader_task: Optional[asyncio.Task] = None

    def _resolve_cloudflared(self) -> Optional[str]:
        # Check project root folder
        local_exe = Path(__file__).resolve().parent.parent / "cloudflared.exe"
        if local_exe.exists():
            return str(local_exe)
        # Check system PATH
        which = shutil.which("cloudflared")
        if which:
            return which
        return None

    async def start(self, timeout: int = 25) -> Optional[str]:
        """Start tunnel: prioritizes reliable SSH tunnel (unblocked in RU), with cloudflared/localtunnel fallback."""
        url = await self._start_ssh_tunnel(timeout=15)
        if url:
            return url

        if self.cloudflared_path and Path(self.cloudflared_path).exists():
            url = await self._start_cloudflared(timeout=18)
            if url:
                return url

        return await self._start_localtunnel(timeout=15)

    async def _start_ssh_tunnel(self, timeout: int = 15) -> Optional[str]:
        """Start a resilient SSH reverse tunnel via localhost.run (Let's Encrypt TLS)."""
        ssh_bin = shutil.which("ssh") or "C:\\Windows\\System32\\OpenSSH\\ssh.exe"
        if not shutil.which("ssh") and not Path(ssh_bin).exists():
            return None

        cmd = [
            ssh_bin,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-o", "ExitOnForwardFailure=yes",
            "-R", f"80:127.0.0.1:{self.port}",
            "nokey@localhost.run"
        ]
        logger.info("Launching resilient SSH HTTPS tunnel: %s", " ".join(cmd))

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            logger.warning("Could not launch ssh process: %s", e)
            return None

        pattern = re.compile(r"https://[a-zA-Z0-9-]+\.lhr\.life")
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.process.returncode is not None:
                break
            line = await self.process.stdout.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue

            text = line.decode("utf-8", errors="ignore").strip()
            match = pattern.search(text)
            if match:
                self.public_url = match.group(0)
                set_current_tunnel_url(self.public_url)
                logger.info("SSH HTTPS tunnel established: %s", self.public_url)
                self._reader_task = asyncio.create_task(self._drain_output())
                return self.public_url

        logger.warning("SSH tunnel failed to yield a public URL within %ds", timeout)
        return None


    async def _start_cloudflared(self, timeout: int) -> Optional[str]:
        cmd = [
            self.cloudflared_path,
            "tunnel",
            "--protocol", "http2",
            "--edge-ip-version", "4",
            "--url", f"http://127.0.0.1:{self.port}"
        ]
        logger.info("Launching Cloudflare Quick Tunnel: %s", " ".join(cmd))

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.process.returncode is not None:
                logger.error("cloudflared process terminated prematurely with code %s", self.process.returncode)
                break

            line = await self.process.stderr.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue

            text = line.decode("utf-8", errors="ignore").strip()
            match = pattern.search(text)
            if match:
                self.public_url = match.group(0)
                set_current_tunnel_url(self.public_url)
                logger.info("Cloudflare Quick Tunnel established: %s", self.public_url)
                self._reader_task = asyncio.create_task(self._drain_output())
                return self.public_url

        logger.warning("Cloudflare Quick Tunnel failed to yield a public URL within %ds", timeout)
        return None

    async def _start_localtunnel(self, timeout: int) -> Optional[str]:
        npx_path = shutil.which("npx") or shutil.which("npx.cmd")
        if not npx_path:
            logger.error("Neither cloudflared nor npx (localtunnel) is available.")
            return None

        cmd = [npx_path, "localtunnel", "--port", str(self.port)]
        logger.info("Launching localtunnel fallback: %s", " ".join(cmd))

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        pattern = re.compile(r"https://[a-zA-Z0-9-]+\.loca\.lt")
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            line = await self.process.stdout.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue

            text = line.decode("utf-8", errors="ignore").strip()
            match = pattern.search(text)
            if match:
                self.public_url = match.group(0)
                set_current_tunnel_url(self.public_url)
                logger.info("Localtunnel established: %s", self.public_url)
                self._reader_task = asyncio.create_task(self._drain_output())
                return self.public_url

        return None

    async def _drain_stream(self, stream):
        """Read lines continuously to prevent Windows pipe buffer from blocking."""
        try:
            while self.process and self.process.returncode is None:
                line = await stream.readline()
                if not line:
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _drain_output(self):
        """Continuously drain both process stdout and stderr concurrently without filling OS buffer."""
        tasks = []
        if self.process:
            if self.process.stdout:
                tasks.append(asyncio.create_task(self._drain_stream(self.process.stdout)))
            if self.process.stderr:
                tasks.append(asyncio.create_task(self._drain_stream(self.process.stderr)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        """Terminate tunnel process."""
        set_current_tunnel_url(None)
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()

        if self.process and self.process.returncode is None:
            logger.info("Stopping tunnel process (PID %s)...", self.process.pid)
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=3.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            logger.info("Tunnel stopped.")
