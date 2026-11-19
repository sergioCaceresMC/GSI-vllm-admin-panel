import json
import os
import runpy
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from main import app
from vllm_admin import adapters


CONFIG = {
    "model": "org/model",
    "served_model_name": "local",
    "gpu_memory_utilization": 0.8,
    "max_model_len": 2048,
    "max_num_seqs": 2,
}


class InferencePortTests(unittest.TestCase):
    def test_launcher_and_probe_use_the_same_port(self):
        launcher = runpy.run_path(str(Path(__file__).resolve().parents[1] / "start-vllm.py"))["main"]
        for environment, expected_port in (({}, "8000"), ({"VLLM_PORT": "8001"}, "8001")):
            with self.subTest(port=expected_port):
                with (
                    patch.dict(os.environ, environment, clear=True),
                    patch("shutil.which", return_value="/example/vllm"),
                    patch.object(Path, "read_text", return_value=json.dumps(CONFIG)),
                    patch("os.execv") as execute,
                    patch.object(adapters.urllib.request, "urlopen") as urlopen,
                ):
                    launcher()
                    urlopen.return_value.__enter__.return_value.status = 200
                    self.assertTrue(adapters.health_ready())
                args = execute.call_args.args[1]
                self.assertEqual(args[args.index("--port") + 1], expected_port)
                urlopen.assert_called_once_with(f"http://127.0.0.1:{expected_port}/health", timeout=2)

    def test_invalid_ports_are_rejected(self):
        launcher = runpy.run_path(str(Path(__file__).resolve().parents[1] / "start-vllm.py"))["main"]
        for port in ("invalid", "0", "65536"):
            with self.subTest(port=port):
                with (
                    patch.dict(os.environ, {"VLLM_PORT": port}),
                    patch("os.execv") as execute,
                    patch.object(adapters.urllib.request, "urlopen") as urlopen,
                ):
                    with self.assertRaisesRegex(SystemExit, "VLLM_PORT"):
                        launcher()
                    self.assertFalse(adapters.health_ready())
                execute.assert_not_called()
                urlopen.assert_not_called()


class DashboardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)

    async def test_dashboard_and_assets(self):
        for path, media_type in (
            ("/", "text/html"),
            ("/static/dashboard.css", "text/css"),
            ("/static/dashboard.js", "javascript"),
            ("/static/api.js", "javascript"),
        ):
            with self.subTest(path=path):
                response = await self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(media_type, response.headers["content-type"])

    async def test_status(self):
        for active, healthy, state in (
            (False, False, "stopped"),
            (True, False, "starting"),
            (True, True, "ready"),
        ):
            with self.subTest(state=state):
                result = CompletedProcess([], 0 if active else 3, "active" if active else "inactive")
                with patch.object(adapters, "systemctl", return_value=result) as systemctl:
                    with patch.object(adapters, "health_ready", return_value=healthy) as health:
                        response = await self.client.get("/api/status")
                self.assertEqual(response.json(), {"running": active, "ready": healthy, "state": state})
                systemctl.assert_called_once_with("is-active")
                self.assertEqual(health.call_count, int(active))

    async def test_metrics_without_gpu(self):
        with patch.object(adapters.shutil, "which", return_value=None):
            response = await self.client.get("/api/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"cpu", "ram", "gpu"})
        self.assertIsNone(response.json()["gpu"])

    async def test_config_read_and_save(self):
        with patch.object(adapters, "read_config", return_value=CONFIG):
            self.assertEqual((await self.client.get("/api/config")).json(), CONFIG)

        with patch.object(adapters, "write_config", return_value=CompletedProcess([], 0)) as write:
            response = await self.client.put("/api/config", json=CONFIG)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["restart_required"])
        self.assertEqual(json.loads(write.call_args.args[0]), {**CONFIG, "auto_start": False})

    async def test_invalid_config_does_not_call_helper(self):
        with patch.object(adapters, "write_config") as write:
            response = await self.client.put("/api/config", json={**CONFIG, "max_num_seqs": 0})
        self.assertEqual(response.status_code, 422)
        write.assert_not_called()

    async def test_failed_config_write(self):
        with patch.object(adapters, "write_config", return_value=CompletedProcess([], 1, "", " denied\n")):
            response = await self.client.put("/api/config", json=CONFIG)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "denied"})

    async def test_service_controls(self):
        for command in ("start", "stop", "restart"):
            with self.subTest(command=command):
                with patch.object(adapters, "systemctl", return_value=CompletedProcess([], 0)) as systemctl:
                    response = await self.client.post(f"/api/{command}")
                self.assertEqual(response.status_code, 200)
                systemctl.assert_called_once_with(command)

    async def test_autostart(self):
        for enabled, command in ((True, "enable"), (False, "disable")):
            with self.subTest(enabled=enabled):
                state = "enabled" if enabled else "disabled"
                with patch.object(adapters, "systemctl", return_value=CompletedProcess([], 0, state)) as systemctl:
                    self.assertEqual((await self.client.get("/api/autostart")).json(), {"enabled": enabled})
                    systemctl.assert_called_once_with("is-enabled")
                    systemctl.reset_mock()
                    response = await self.client.put("/api/autostart", json={"enabled": enabled})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["enabled"], enabled)
                systemctl.assert_called_once_with(command)
