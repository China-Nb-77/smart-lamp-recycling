#!/usr/bin/env python3
"""Launcher that runs two Java service jars and proxies their logs.

Usage (development):
  python launcher.py --jar1 "wechat_payment_fix/pay-demo/target/pay-demo-patch-0.0.1-SNAPSHOT.jar" \
    --jar2 "fulfillment - 副本/target/fulfillment-1.0.0.jar"

When bundled with PyInstaller use --add-data to include the jars and run the single exe.
"""
from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import threading
from typing import List

# Eager-import the Python service package so PyInstaller includes it when building the onefile.
try:
    import image_quote_system  # noqa: F401
except Exception:
    # If running in environments where package is not present, Python service won't be started.
    image_quote_system = None


def resource_path(name: str) -> str:
    # When bundled by PyInstaller, resources are extracted to _MEIPASS
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, name)


def stream_output(prefix: str, stream) -> None:
    for line in iter(stream.readline, b""):
        try:
            text = line.decode("utf-8", errors="replace").rstrip("\n")
        except Exception:
            text = str(line)
        print(f"[{prefix}] {text}")
    stream.close()


def start_service(java_cmd: str, jar: str, name: str, extra_args: List[str]) -> subprocess.Popen:
    jar_path = jar if os.path.isabs(jar) else resource_path(jar)
    if not os.path.exists(jar_path):
        raise FileNotFoundError(f"Jar not found: {jar_path}")
    cmd = [java_cmd, "-jar", jar_path] + extra_args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    t = threading.Thread(target=stream_output, args=(name, proc.stdout), daemon=True)
    t.start()
    return proc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jar1", required=False, default="", help="路径到第一个 jar（相对或绝对）")
    parser.add_argument("--jar2", required=False, default="", help="路径到第二个 jar（相对或绝对）")
    parser.add_argument("--java", default="java", help="Java 可执行文件路径（默认 java）")
    parser.add_argument("--args1", default="", help="传递给第一个服务的额外参数（用空格分隔）")
    parser.add_argument("--args2", default="", help="传递给第二个服务的额外参数（用空格分隔）")
    parser.add_argument("--skip-jars", action="store_true", help="跳过启动 Java jars（仅启动 Python 服务）")
    parser.add_argument("--start-python-service", action="store_true", help="一并启动 image_quote_system (Python 服务)")
    parser.add_argument("--py-host", default="127.0.0.1", help="Python 服务 host")
    parser.add_argument("--py-port", type=int, default=8000, help="Python 服务 port")
    parser.add_argument("--py-config", default="configs", help="Python 服务 config dir 相对路径")
    args = parser.parse_args()

    extra1 = shlex.split(args.args1)
    extra2 = shlex.split(args.args2)

    procs: List[subprocess.Popen] = []
    py_thread = None

    def shutdown(signum, frame):
        print("Shutting down services...")
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for p in procs:
            try:
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        if not getattr(args, "skip_jars", False):
            if not args.jar1 or not args.jar2:
                print("Error: --jar1 and --jar2 are required unless --skip-jars is used")
                return 2
            print("Starting service 1 (jar1)")
            p1 = start_service(args.java, args.jar1, "service1", extra1)
            procs.append(p1)

            print("Starting service 2 (jar2)")
            p2 = start_service(args.java, args.jar2, "service2", extra2)
            procs.append(p2)
        else:
            print("Skipping Java services (--skip-jars set)")

        if getattr(args, "start_python_service", False):
            if image_quote_system is None:
                print("Python package image_quote_system not available; skipping Python service.")
            else:
                def run_py():
                    try:
                        from image_quote_system.serving.api import serve_api

                        print(f"Starting Python service at {args.py_host}:{args.py_port}")
                        serve_api(host=args.py_host, port=args.py_port, config_dir=args.py_config)
                    except Exception as e:  # pragma: no cover
                        print("Python service failed:", e)

                py_thread = threading.Thread(target=run_py, daemon=True)
                py_thread.start()

        # wait until one exits
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    print(f"Process exited with code {ret}. Shutting down other processes.")
                    shutdown(0, None)
            # If Python server thread died, also shutdown
            if py_thread is not None and not py_thread.is_alive():
                print("Python service thread stopped; shutting down.")
                shutdown(0, None)
            # avoid busy loop
            signal.pause() if hasattr(signal, "pause") else threading.Event().wait(1)

    except FileNotFoundError as exc:
        print(str(exc))
        return 2
    except Exception as exc:  # pragma: no cover
        print("Launcher error:", exc)
        shutdown(0, None)


if __name__ == "__main__":
    raise SystemExit(main())
