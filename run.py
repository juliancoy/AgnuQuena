#!/usr/bin/env python3
"""Run the AgnuQuena browser lab and its Selenium test browser in Docker."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "website"
SERVER_SCRIPT = ROOT / "docker" / "static-server.mjs"
SCREENSHOT = ROOT / "build" / "selenium" / "acoustic-lab.png"

PROJECT_LABEL = "org.agnuquena.browser-lab"
PROJECT_LABEL_VALUE = "managed"
NETWORK = "agnuquena-lab"
WEB_CONTAINER = "agnuquena-web"
SELENIUM_CONTAINER = "agnuquena-selenium"
WEB_ALIAS = "web"

NODE_IMAGE = os.environ.get("AGNUQUENA_NODE_IMAGE", "node:24-alpine")
SELENIUM_IMAGE = os.environ.get(
    "AGNUQUENA_SELENIUM_IMAGE",
    "selenium/standalone-chrome:latest",
)


class LauncherError(RuntimeError):
    pass


def run_command(
    command: list[str],
    *,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def docker(*arguments: str, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_command(["docker", *arguments], capture=capture, check=check)


def require_prerequisites() -> None:
    if not WEB_ROOT.is_dir():
        raise LauncherError(f"Missing browser source directory: {WEB_ROOT}")
    if not SERVER_SCRIPT.is_file():
        raise LauncherError(f"Missing Node server entrypoint: {SERVER_SCRIPT}")
    try:
        docker("info", capture=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise LauncherError("Docker is not installed or the Docker daemon is unavailable.") from error


def container_exists(name: str) -> bool:
    result = docker("container", "inspect", name, capture=True, check=False)
    return result.returncode == 0


def managed_container(name: str) -> bool:
    result = docker(
        "container",
        "inspect",
        "--format",
        f'{{{{index .Config.Labels "{PROJECT_LABEL}"}}}}',
        name,
        capture=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == PROJECT_LABEL_VALUE


def remove_managed_container(name: str) -> None:
    if not container_exists(name):
        return
    if not managed_container(name):
        raise LauncherError(
            f"Refusing to replace container {name!r}: it is not managed by this launcher."
        )
    docker("container", "rm", "--force", name)


def ensure_network() -> None:
    result = docker("network", "inspect", NETWORK, capture=True, check=False)
    if result.returncode != 0:
        docker("network", "create", "--label", f"{PROJECT_LABEL}={PROJECT_LABEL_VALUE}", NETWORK)


def ensure_image(image: str) -> None:
    if docker("image", "inspect", image, capture=True, check=False).returncode == 0:
        return
    print(f"Pulling {image}...")
    docker("pull", image)


def gpu_arguments() -> list[str]:
    render_device = Path("/dev/dri/renderD128")
    if not render_device.exists():
        return []
    arguments = ["--device", f"{render_device}:{render_device}"]
    try:
        render_gid = render_device.stat().st_gid
    except OSError:
        return arguments
    return [*arguments, "--group-add", str(render_gid)]


def start_web(web_port: int) -> None:
    remove_managed_container(WEB_CONTAINER)
    docker(
        "run",
        "--detach",
        "--name",
        WEB_CONTAINER,
        "--hostname",
        WEB_CONTAINER,
        "--label",
        f"{PROJECT_LABEL}={PROJECT_LABEL_VALUE}",
        "--network",
        NETWORK,
        "--network-alias",
        WEB_ALIAS,
        "--restart",
        "unless-stopped",
        "--publish",
        f"127.0.0.1:{web_port}:8080",
        "--mount",
        f"type=bind,src={WEB_ROOT},dst=/srv/site,readonly",
        "--mount",
        f"type=bind,src={SERVER_SCRIPT},dst=/app/static-server.mjs,readonly",
        "--health-cmd",
        "wget -q -O - http://127.0.0.1:8080/healthz || exit 1",
        "--health-interval",
        "2s",
        "--health-timeout",
        "2s",
        "--health-retries",
        "15",
        NODE_IMAGE,
        "node",
        "/app/static-server.mjs",
    )


def start_selenium(selenium_port: int, vnc_port: int) -> None:
    remove_managed_container(SELENIUM_CONTAINER)
    docker(
        "run",
        "--detach",
        "--name",
        SELENIUM_CONTAINER,
        "--hostname",
        SELENIUM_CONTAINER,
        "--label",
        f"{PROJECT_LABEL}={PROJECT_LABEL_VALUE}",
        "--network",
        NETWORK,
        "--restart",
        "unless-stopped",
        "--shm-size",
        "2g",
        "--publish",
        f"127.0.0.1:{selenium_port}:4444",
        "--publish",
        f"127.0.0.1:{vnc_port}:7900",
        "--env",
        "SE_NODE_MAX_SESSIONS=1",
        "--env",
        "SE_NODE_OVERRIDE_MAX_SESSIONS=true",
        "--env",
        "SE_VNC_NO_PASSWORD=1",
        *gpu_arguments(),
        SELENIUM_IMAGE,
    )


def http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 10,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    return json.loads(data) if data else {}


def wait_for_url(url: str, description: str, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 300:
                    return
        except (OSError, urllib.error.URLError) as error:
            last_error = error
        time.sleep(1)
    raise LauncherError(f"Timed out waiting for {description} at {url}: {last_error}")


def webdriver_value(response: dict[str, Any]) -> Any:
    value = response.get("value")
    if isinstance(value, dict) and "error" in value:
        raise LauncherError(f"WebDriver error: {value.get('error')}: {value.get('message')}")
    return value


def execute_script(webdriver: str, session_id: str, script: str) -> Any:
    response = http_json(
        "POST",
        f"{webdriver}/session/{session_id}/execute/sync",
        {"script": script, "args": []},
    )
    return webdriver_value(response)


def create_webdriver_session(webdriver: str) -> str:
    chrome_arguments = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu-sandbox",
        "--enable-webgl",
        "--ignore-gpu-blocklist",
        "--use-gl=angle",
        "--use-angle=gl",
        "--enable-unsafe-webgpu",
        "--enable-features=Vulkan",
        "--unsafely-treat-insecure-origin-as-secure=http://web:8080",
        "--window-size=1440,1000",
    ]
    response = http_json(
        "POST",
        f"{webdriver}/session",
        {
            "capabilities": {
                "alwaysMatch": {
                    "browserName": "chrome",
                    "goog:chromeOptions": {"args": chrome_arguments},
                }
            }
        },
        timeout=30,
    )
    value = webdriver_value(response)
    session_id = response.get("sessionId")
    if not session_id and isinstance(value, dict):
        session_id = value.get("sessionId")
    if not session_id:
        raise LauncherError(f"Selenium did not return a session id: {response}")
    return str(session_id)


def wait_for_lab(webdriver: str, session_id: str, timeout: float = 30) -> dict[str, Any]:
    script = """
const badge = document.querySelector("#gpuBadge");
return {
  ready: document.readyState === "complete"
    && badge
    && !badge.textContent.includes("Detecting"),
  title: document.title,
  badge: badge ? badge.textContent.trim() : "",
  navigatorGpu: Boolean(navigator.gpu),
  canvas: Boolean(document.querySelector("#pressureCanvas")),
  fieldModes: document.querySelector("#fieldSelect")?.options.length || 0,
  fingerings: document.querySelector("#noteSelect")?.options.length || 0,
	  cfd: window.__agnuquenaCFD?.configuration || null,
	  volume3d: window.__agnuquena3D || null,
};
"""
    deadline = time.monotonic() + timeout
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        value = execute_script(webdriver, session_id, script)
        if isinstance(value, dict):
            state = value
            if value.get("ready"):
                return state
        time.sleep(0.5)
    raise LauncherError(f"The acoustic lab did not become ready: {state}")


def capture_screenshot(webdriver: str, session_id: str) -> Path:
    response = http_json("GET", f"{webdriver}/session/{session_id}/screenshot")
    encoded = webdriver_value(response)
    if not isinstance(encoded, str):
        raise LauncherError("Selenium did not return a PNG screenshot.")
    SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    SCREENSHOT.write_bytes(base64.b64decode(encoded))
    return SCREENSHOT


def run_smoke_test(selenium_port: int, require_webgpu: bool) -> dict[str, Any]:
    webdriver = f"http://127.0.0.1:{selenium_port}"
    session_id = create_webdriver_session(webdriver)
    try:
        target = f"http://{WEB_ALIAS}:8080/acoustics.html"
        webdriver_value(
            http_json(
                "POST",
                f"{webdriver}/session/{session_id}/url",
                {"url": target},
                timeout=30,
            )
        )
        state = wait_for_lab(webdriver, session_id)
        if state.get("title") != "AgnuQuena Acoustic Lab":
            raise LauncherError(f"Unexpected page title: {state.get('title')!r}")
        if not state.get("canvas") or state.get("fieldModes") != 3 or state.get("fingerings") != 6:
            raise LauncherError(f"The CFD controls are incomplete: {state}")
        volume = state.get("volume3d")
        if not isinstance(volume, dict) or not volume.get("ready") or volume.get("pointCount", 0) < 1000:
            raise LauncherError(f"The Three.js 3D CFD volume is unavailable: {state}")

        webgpu_active = state.get("badge") == "WebGPU 3D LES"
        if require_webgpu and not webgpu_active:
            raise LauncherError(
                f"WebGPU was required but Selenium reported {state.get('badge')!r}."
            )

        if webgpu_active:
            execute_script(
                webdriver,
                session_id,
                'document.querySelector("#toggleRun").click(); return true;',
            )
            deadline = time.monotonic() + 15
            simulated_ms = 0.0
            while time.monotonic() < deadline:
                text = execute_script(
                    webdriver,
                    session_id,
                    'return document.querySelector("#simTime").textContent;',
                )
                try:
                    simulated_ms = float(str(text).split()[0])
                except (TypeError, ValueError):
                    simulated_ms = 0.0
                if simulated_ms > 0:
                    break
                time.sleep(0.5)
            if simulated_ms <= 0:
                raise LauncherError("WebGPU initialized, but the CFD clock did not advance.")
            state["simulatedMs"] = simulated_ms
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                volume = execute_script(
                    webdriver,
                    session_id,
                    "return window.__agnuquena3D;",
                )
                if isinstance(volume, dict) and volume.get("updates", 0) > 0:
                    state["volume3d"] = volume
                    break
                time.sleep(0.5)
            else:
                raise LauncherError("The Three.js 3D CFD volume did not receive live solver samples.")

        execute_script(
            webdriver,
            session_id,
            'document.querySelector(".inspection-grid").scrollIntoView({block: "center"}); return true;',
        )
        time.sleep(1)
        state["screenshot"] = str(capture_screenshot(webdriver, session_id))
        return state
    finally:
        try:
            http_json("DELETE", f"{webdriver}/session/{session_id}")
        except Exception:
            pass


def command_up(args: argparse.Namespace) -> None:
    require_prerequisites()
    ensure_image(NODE_IMAGE)
    ensure_image(SELENIUM_IMAGE)
    ensure_network()
    start_web(args.web_port)
    start_selenium(args.selenium_port, args.vnc_port)
    wait_for_url(f"http://127.0.0.1:{args.web_port}/healthz", "Node web server")
    wait_for_url(f"http://127.0.0.1:{args.selenium_port}/status", "Selenium")
    result = run_smoke_test(args.selenium_port, args.require_webgpu)
    print(json.dumps(result, indent=2, sort_keys=True))
    print()
    print(f"Lab:      http://127.0.0.1:{args.web_port}/acoustics.html")
    print(f"Selenium: http://127.0.0.1:{args.selenium_port}")
    print(f"Browser:  http://127.0.0.1:{args.vnc_port}")


def command_test(args: argparse.Namespace) -> None:
    wait_for_url(f"http://127.0.0.1:{args.web_port}/healthz", "Node web server")
    wait_for_url(f"http://127.0.0.1:{args.selenium_port}/status", "Selenium")
    print(json.dumps(run_smoke_test(args.selenium_port, args.require_webgpu), indent=2, sort_keys=True))


def command_down(_: argparse.Namespace) -> None:
    for name in (SELENIUM_CONTAINER, WEB_CONTAINER):
        remove_managed_container(name)
    network = docker("network", "inspect", NETWORK, capture=True, check=False)
    if network.returncode == 0:
        docker("network", "rm", NETWORK, check=False)


def command_status(_: argparse.Namespace) -> None:
    result = docker(
        "ps",
        "--all",
        "--filter",
        f"label={PROJECT_LABEL}={PROJECT_LABEL_VALUE}",
        "--format",
        "table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}",
        capture=True,
    )
    print(result.stdout.rstrip())


def command_logs(args: argparse.Namespace) -> None:
    name = WEB_CONTAINER if args.service == "web" else SELENIUM_CONTAINER
    if not managed_container(name):
        raise LauncherError(f"{name} is not running as a managed container.")
    command = ["docker", "logs", "--tail", str(args.tail)]
    if args.follow:
        command.append("--follow")
    command.append(name)
    subprocess.run(command, cwd=ROOT, check=False)


def add_port_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--web-port", type=int, default=4173)
    parser.add_argument("--selenium-port", type=int, default=4444)
    parser.add_argument("--vnc-port", type=int, default=7900)
    parser.add_argument(
        "--require-webgpu",
        action="store_true",
        help="fail the Selenium test unless the WebGPU CFD backend initializes",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    up = subparsers.add_parser("up", help="start both containers and run the smoke test")
    add_port_arguments(up)
    up.set_defaults(handler=command_up)

    test = subparsers.add_parser("test", help="test the already-running containers")
    add_port_arguments(test)
    test.set_defaults(handler=command_test)

    down = subparsers.add_parser("down", help="remove both managed containers and their network")
    down.set_defaults(handler=command_down)

    status = subparsers.add_parser("status", help="show managed container status")
    status.set_defaults(handler=command_status)

    logs = subparsers.add_parser("logs", help="show logs for one service")
    logs.add_argument("service", choices=("web", "selenium"))
    logs.add_argument("--tail", type=int, default=100)
    logs.add_argument("--follow", action="store_true")
    logs.set_defaults(handler=command_logs)
    return parser


def main() -> int:
    parser = build_parser()
    arguments = sys.argv[1:] or ["up"]
    args = parser.parse_args(arguments)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    try:
        args.handler(args)
    except (LauncherError, subprocess.CalledProcessError, urllib.error.URLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
