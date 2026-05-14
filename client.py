from flask import Flask, jsonify
from flask import Flask, jsonify, request
import os
import requests
import random
import uuid
from datetime import datetime
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

PROCESSOR_URL = os.environ.get("PROCESSOR_URL", "http://processor:5001/process")


def _make_order():
    order_id = str(uuid.uuid4())
    return {
        "order_id": order_id,
        "item": random.choice(["apple", "banana", "widget", "gadget"]),
        "price": round(random.uniform(1, 100), 2),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": f"order {order_id}"
    }


def _post_order(session, payload, timeout=10):
    start = time.perf_counter()
    try:
        resp = session.post(PROCESSOR_URL, json=payload, timeout=timeout)
        elapsed = time.perf_counter() - start
        return True, elapsed, resp.status_code, resp.json() if resp.headers.get('Content-Type','').startswith('application/json') else resp.text
    except Exception as e:
        elapsed = time.perf_counter() - start
        return False, elapsed, None, str(e)


@app.route("/buy", methods=["GET"])
def buy():
    # params: count, concurrency, mode
    mode = request.args.get("mode", "single")
    try:
        count = int(request.args.get("count", 1))
        concurrency = int(request.args.get("concurrency", 1))
    except ValueError:
        return jsonify({"error": "count and concurrency must be integers"}), 400

    if mode == "low":
        count = int(request.args.get("count", 5))
        concurrency = int(request.args.get("concurrency", 1))
    elif mode == "high":
        count = int(request.args.get("count", 500))
        concurrency = int(request.args.get("concurrency", 50))

    if count < 1 or concurrency < 1:
        return jsonify({"error": "count and concurrency must be >= 1"}), 400

    payloads = [_make_order() for _ in range(count)]

    results = []
    start_all = time.perf_counter()
    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=min(concurrency, count)) as ex:
            futures = [ex.submit(_post_order, session, p) for p in payloads]
            for fut in as_completed(futures):
                results.append(fut.result())
    total_time = time.perf_counter() - start_all

    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]
    latencies = [r[1] for r in results if r[1] is not None]

    summary = {
        "requested": count,
        "concurrency": concurrency,
        "total_time_s": round(total_time, 4),
        "success_count": len(successes),
        "failure_count": len(failures),
        "min_latency_s": round(min(latencies), 4) if latencies else None,
        "max_latency_s": round(max(latencies), 4) if latencies else None,
        "mean_latency_s": round(statistics.mean(latencies), 4) if latencies else None,
    }

    # include a small sample of responses
    sample_responses = [r[3] for r in successes[:5]]

    return jsonify({"summary": summary, "sample_responses": sample_responses})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "client running", "processor_url": PROCESSOR_URL})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))