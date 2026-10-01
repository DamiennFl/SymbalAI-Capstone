#!/usr/bin/env python3
"""
Probe health/readiness endpoints while the service is under load.

Typical use (from repo root after container is up on localhost:8000):
    python -m uv run python code/backend/scripts/probe_freeze.py --audio 
    "<File path to .flac, .wav, or .mp3 file>" --audio-repeat 5 --audio-delay 1 --duration 12

Key signals:
  - Timeouts/connection errors -> likely process freeze or worker death.
  - Large latency spikes -> requests are queuing or CPU is saturated.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, List, Optional, Tuple

import httpx


@dataclass
class ProbeResult:
    when: datetime
    endpoint: str
    status: Optional[int]
    latency_ms: float
    error: Optional[str]


def probe_loop(
    client: httpx.Client,
    base_url: str,
    endpoints: List[str],
    interval: float,
    timeout: float,
    stop: threading.Event,
    sink: Deque[ProbeResult],
    warn_timeout_ms: float,
    consecutive_fail_warn: int,
) -> None:
    """Continuously ping endpoints until stop is set."""
    consecutive_failures = 0
    while not stop.is_set():
        for ep in endpoints:
            start = time.perf_counter()
            status: Optional[int] = None
            err: Optional[str] = None
            try:
                resp = client.get(f"{base_url.rstrip('/')}{ep}", timeout=timeout)
                status = resp.status_code
            except Exception as exc:  # broad to catch timeouts/connection errors
                err = str(exc)

            latency_ms = (time.perf_counter() - start) * 1000
            sink.append(
                ProbeResult(
    when=datetime.now(timezone.utc),
                    endpoint=ep,
                    status=status,
                    latency_ms=latency_ms,
                    error=err,
                )
            )

            ok = err is None and status and 200 <= status < 400
            if ok:
                consecutive_failures = 0
            else:
                consecutive_failures += 1

            if not ok:
                print(
                    f"[{datetime.now(timezone.utc).isoformat()}] FAIL {ep} "
                    f"status={status} err={err} {latency_ms:.0f}ms",
                    file=sys.stderr,
                )
            elif latency_ms >= warn_timeout_ms:
                print(
                    f"[{datetime.now(timezone.utc).isoformat()}] WARN {ep} "
                    f"slow {latency_ms:.0f}ms (queuing?)",
                    file=sys.stderr,
                )

            if consecutive_failures >= consecutive_fail_warn:
                print(
                    f"[{datetime.now(timezone.utc).isoformat()}] ALERT: "
                    f"{consecutive_failures} consecutive failures "
                    f"(freeze or worker crash likely)",
                    file=sys.stderr,
                )

            if stop.is_set():
                break
        stop.wait(interval)


def run_audio_job(
    client: httpx.Client,
    base_url: str,
    audio_path: str,
    repeat: int,
    delay: float,
    timeout: float,
    stop: threading.Event,
    use_async: bool,
    poll_interval: float,
) -> None:
    """Send one or more /detect/audio requests to generate load."""
    sync_url = f"{base_url.rstrip('/')}/detect/audio"
    async_url = f"{base_url.rstrip('/')}/detect/audio/async"
    status_url = f"{base_url.rstrip('/')}/detect/audio/async/{{job_id}}"
    for i in range(repeat):
        if stop.is_set():
            break
        start = time.perf_counter()
        try:
            with open(audio_path, "rb") as fh:
                files = {"file": (audio_path, fh, "audio/wav")}
                if use_async:
                    job_resp = client.post(async_url, files=files, timeout=timeout)
                    job_resp.raise_for_status()
                    job_id = job_resp.json().get("job_id")
                    print(
                        f"[{datetime.now(timezone.utc).isoformat()}] AUDIO {i+1}/{repeat} "
                        f"queued job={job_id}",
                        file=sys.stderr,
                    )
                    # Poll until done/error or stop
                    while not stop.is_set():
                        poll_start = time.perf_counter()
                        r = client.get(
                            status_url.format(job_id=job_id),
                            timeout=timeout,
                        )
                        r.raise_for_status()
                        js = r.json()
                        status = js.get("status")
                        if status in ("done", "error"):
                            took = (time.perf_counter() - start) * 1000
                            if status == "done":
                                print(
                                    f"[{datetime.now(timezone.utc).isoformat()}] AUDIO {i+1}/{repeat} "
                                    f"done {took:.0f}ms",
                                    file=sys.stderr,
                                )
                            else:
                                print(
                                    f"[{datetime.now(timezone.utc).isoformat()}] AUDIO {i+1}/{repeat} "
                                    f"ERROR {js.get('error')} {took:.0f}ms",
                                    file=sys.stderr,
                                )
                            break
                        stop.wait(poll_interval)
                        # Adjust start to include polling overhead
                        continue
                else:
                    resp = client.post(sync_url, files=files, timeout=timeout)
                    took = (time.perf_counter() - start) * 1000
                    print(
                        f"[{datetime.now(timezone.utc).isoformat()}] AUDIO {i+1}/{repeat} "
                        f"status={resp.status_code} {took:.0f}ms",
                        file=sys.stderr,
                    )
        except Exception as exc:
            took = (time.perf_counter() - start) * 1000
            print(
                f"[{datetime.now(timezone.utc).isoformat()}] AUDIO {i+1}/{repeat} "
                f"ERROR {exc} {took:.0f}ms",
                file=sys.stderr,
            )
        stop.wait(delay)


def summarize(results: Deque[ProbeResult]) -> Tuple[int, int, float]:
    total = len(results)
    failures = len([r for r in results if r.error or not r.status or r.status >= 400])
    latencies = [r.latency_ms for r in results if not r.error and r.status]
    p95 = percentile(latencies, 95) if latencies else 0.0
    return total, failures, p95


def percentile(data: List[float], pct: float) -> float:
    if not data:
        return 0.0
    data = sorted(data)
    k = (len(data) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(data) - 1)
    if f == c:
        return data[f]
    return data[f] + (data[c] - data[f]) * (k - f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe FastAPI health endpoints to detect freezes/queuing."
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="Service base URL")
    parser.add_argument(
        "--endpoints",
        default="/health,/liveness,/readiness",
        help="Comma-separated list of endpoints to probe",
    )
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between probe cycles")
    parser.add_argument(
        "--timeout", type=float, default=2.0, help="Per-request timeout in seconds"
    )
    parser.add_argument(
        "--warn-slow-ms",
        type=float,
        default=750.0,
        help="Latency threshold that suggests queuing (ms)",
    )
    parser.add_argument(
        "--alert-failures",
        type=int,
        default=3,
        help="Consecutive failures before printing ALERT",
    )
    parser.add_argument(
        "--audio",
        help="Optional path to an audio file to POST to /detect/audio to create load",
    )
    parser.add_argument(
        "--audio-repeat",
        type=int,
        default=1,
        help="How many times to send the audio file (requires --audio)",
    )
    parser.add_argument(
        "--audio-delay",
        type=float,
        default=0.5,
        help="Seconds to wait between audio requests (requires --audio-repeat > 1)",
    )
    parser.add_argument(
        "--audio-async",
        action="store_true",
        help="Use /detect/audio/async and poll job status instead of blocking request",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.5,
        help="Polling interval for async audio jobs (seconds)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0,
        help="Stop after N seconds (0 keeps running until Ctrl+C)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoints = [ep.strip() for ep in args.endpoints.split(",") if ep.strip()]

    stop = threading.Event()
    results: Deque[ProbeResult] = deque(maxlen=2000)

    client = httpx.Client(http2=False)

    probe_thread = threading.Thread(
        target=probe_loop,
        args=(
            client,
            args.base_url,
            endpoints,
            args.interval,
            args.timeout,
            stop,
            results,
            args.warn_slow_ms,
            args.alert_failures,
        ),
        daemon=True,
    )
    probe_thread.start()

    audio_thread: Optional[threading.Thread] = None
    if args.audio:
        audio_thread = threading.Thread(
            target=run_audio_job,
            args=(
                client,
                args.base_url,
                args.audio,
                args.audio_repeat,
                args.audio_delay,
                args.timeout * 5,
                stop,
                args.audio_async,
                args.poll_interval,
            ),
            daemon=True,
        )
        audio_thread.start()

    try:
        if args.duration > 0:
            stop.wait(args.duration)
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        probe_thread.join(timeout=2)
        if audio_thread:
            audio_thread.join(timeout=2)
        client.close()

    total, failures, p95 = summarize(results)
    print(
        f"Summary: {total} probes, {failures} failures, p95 latency {p95:.0f}ms",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
