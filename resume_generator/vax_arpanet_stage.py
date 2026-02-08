"""ARPANET-aware VAX stage scaffolding.

This module provides a thin wrapper around :mod:`resume_generator.vax_stage`
so we can incrementally add ARPANET transport behavior behind a dedicated
feature flag without disrupting the existing VAX pipeline.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from .vax_stage import VaxStageConfig, VaxStagePaths, VaxStageRunner


class VaxArpanetStageRunner:
    """Runs the existing VAX stage and emits ARPANET transfer scaffold output."""

    def __init__(
        self,
        *,
        config: VaxStageConfig,
        repo_root: Path,
        execute_commands: bool = False,
    ) -> None:
        """Initialize the ARPANET-aware stage wrapper.

        Args:
            config: VAX stage configuration.
            repo_root: Repository root path.
            execute_commands: Whether scaffold commands should execute.
        """
        self._delegate = VaxStageRunner(config=config, repo_root=repo_root)
        self._execute_commands = execute_commands

    @property
    def paths(self) -> VaxStagePaths:
        """Expose underlying stage paths for callers/tests."""
        return self._delegate.paths

    def run(self) -> None:
        """Run the wrapped VAX stage and execute ARPANET scaffold steps."""
        self._delegate.run()
        steps: list[str] = ["ARPANET transfer stage scaffold"]
        if not self._execute_commands:
            steps.append("mode: dry-run")
            steps.append("status: command execution skipped")
            self._write_arpanet_transfer_log(steps)
            return

        steps.append("mode: execute")
        try:
            self._start_arpanet_network(steps)
            self._validate_phase2_links(steps)
            self._run_transfer_script(steps)
            self._collect_arpanet_logs(steps)
            steps.append("status: scaffold commands completed")
        except Exception as err:  # noqa: BLE001
            steps.append("status: failed")
            steps.append(f"error: {err}")
            if isinstance(err, RuntimeError):
                raise
            raise RuntimeError(f"ARPANET stage failed: {err}") from err
        finally:
            self._stop_arpanet_network(steps)
            self._write_arpanet_transfer_log(steps)

    def _arpanet_compose_file(self) -> Path:
        return self.paths.repo_root / "docker-compose.arpanet.phase2.yml"

    def _transfer_exec_log_path(self) -> Path:
        return self.paths.vax_build_dir / "arpanet-transfer-exec.log"

    def _phase2_link_test_script_path(self) -> Path:
        return self.paths.repo_root / "arpanet" / "scripts" / "test-phase2-imp-link.sh"

    def _transfer_script_path(self) -> Path:
        candidates = [
            self.paths.repo_root
            / "arpanet"
            / "scripts"
            / "simh-automation"
            / "build-artifact-transfer.ini",
            self.paths.repo_root
            / "arpanet"
            / "scripts"
            / "simh-automation"
            / "authentic-ftp-transfer.ini",
        ]
        for path in candidates:
            if path.exists():
                return path
        raise RuntimeError(
            "Missing transfer script: expected one of "
            f"{', '.join(str(p) for p in candidates)}"
        )

    def _run_command(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, check=True, capture_output=True, text=True)  # noqa: S603

    def _resolve_executable(self, program: str) -> str:
        resolved = shutil.which(program)
        if not resolved:
            raise RuntimeError(f"Required executable not found: {program}")
        return resolved

    def _start_arpanet_network(self, steps: list[str]) -> None:
        compose_file = self._arpanet_compose_file()
        steps.append(f"compose_file: {compose_file}")
        if not compose_file.exists():
            raise RuntimeError(f"Missing ARPANET compose file: {compose_file}")
        docker_bin = self._resolve_executable("docker")
        self._run_command(
            [
                docker_bin,
                "compose",
                "-f",
                str(compose_file),
                "up",
                "-d",
                "vax",
                "imp1",
                "imp2",
                "pdp10",
            ]
        )
        steps.append("network: started (phase2 stack)")

    def _validate_phase2_links(self, steps: list[str]) -> None:
        script_path = self._phase2_link_test_script_path()
        if not script_path.exists():
            raise RuntimeError(f"Missing phase2 link test script: {script_path}")

        bash_bin = self._resolve_executable("bash")
        self._run_command([bash_bin, str(script_path)])
        steps.append("phase2_link_smoke: passed")

    def _run_transfer_script(self, steps: list[str]) -> None:
        script_path = self._transfer_script_path()
        docker_bin = self._resolve_executable("docker")
        container_name = "arpanet-vax"
        guest_script_path = "/machines/data/arpanet-transfer.ini"

        self._run_command(
            [
                docker_bin,
                "cp",
                str(script_path),
                f"{container_name}:{guest_script_path}",
            ]
        )
        exec_command = [
            docker_bin,
            "exec",
            container_name,
            "/usr/bin/simh-vax",
            guest_script_path,
        ]
        exec_result = self._run_transfer_exec_with_retry(exec_command, steps)

        transfer_classification = self._classify_transfer_output(exec_result.stdout)
        if transfer_classification != "ok":
            raise RuntimeError(f"Transfer output validation failed: {transfer_classification}")

        transfer_exec_log = self._transfer_exec_log_path()
        transfer_exec_log.parent.mkdir(parents=True, exist_ok=True)
        transfer_exec_log.write_text(exec_result.stdout, encoding="utf-8")

        steps.append(f"transfer_script: {script_path}")
        steps.append("transfer: executed via docker exec (SIMH automation)")
        steps.append(f"transfer_validation: {transfer_classification}")
        steps.append(f"transfer_output: {transfer_exec_log}")

    def _run_transfer_exec_with_retry(
        self,
        command: Sequence[str],
        steps: list[str],
    ) -> subprocess.CompletedProcess[str]:
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                result = self._run_command(command)
            except subprocess.CalledProcessError as err:
                reason = self._classify_exec_error(err)
                steps.append(f"transfer_exec_attempt_{attempt}: failed ({reason})")
                if attempt >= max_attempts:
                    raise RuntimeError(
                        f"Transfer execution failed after {max_attempts} attempts: {reason}"
                    ) from err
                steps.append(f"transfer_exec_attempt_{attempt}: retrying")
                continue

            steps.append(f"transfer_exec_attempt_{attempt}: ok")
            return result

        raise RuntimeError("Transfer execution retry loop exhausted")

    def _classify_exec_error(self, err: subprocess.CalledProcessError) -> str:
        details = " ".join(
            part
            for part in [
                str(err),
                str(err.stdout or ""),
                str(err.stderr or ""),
            ]
        ).lower()
        if "no such container" in details:
            return "container-missing"
        if "not found" in details:
            return "binary-missing"
        if "permission denied" in details:
            return "permission-denied"
        return "command-failed"

    def _classify_transfer_output(self, output: str) -> str:
        text = output.strip().lower()
        if not text:
            return "empty-output"

        fatal_markers = (
            "fatal",
            "segmentation fault",
            "panic",
            "cannot open",
            "no such file",
            "connection refused",
        )
        if any(marker in text for marker in fatal_markers):
            return "fatal-marker-detected"
        return "ok"

    def _collect_arpanet_logs(self, steps: list[str]) -> None:
        build_id = datetime.now(UTC).strftime("arpanet-stage-%Y%m%d-%H%M%S")
        python_bin = self._resolve_executable("python")
        self._run_command(
            [
                python_bin,
                "-m",
                "arpanet_logging",
                "collect",
                "--build-id",
                build_id,
                "--components",
                "vax",
                "imp1",
                "imp2",
                "pdp10",
                "--duration",
                "1",
                "--path",
                str(self.paths.build_dir / "arpanet-logs"),
            ]
        )
        steps.append("logs: collected via arpanet_logging CLI (scaffold)")

    def _stop_arpanet_network(self, steps: list[str]) -> None:
        compose_file = self._arpanet_compose_file()
        if not compose_file.exists():
            steps.append("network: skip down (compose file missing)")
            return
        docker_bin = shutil.which("docker")
        if not docker_bin:
            steps.append("network: skip down (docker unavailable)")
            return
        subprocess.run(  # noqa: S603
            [docker_bin, "compose", "-f", str(compose_file), "down"],
            check=False,
            capture_output=True,
            text=True,
        )
        steps.append("network: stopped")

    def _write_arpanet_transfer_log(self, steps: Sequence[str]) -> None:
        transfer_log = self.paths.site_dir / "arpanet-transfer.log"
        transfer_log.write_text("\n".join(steps).rstrip() + "\n", encoding="utf-8")
