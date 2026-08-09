import os
import threading
import time
from typing import Any, Dict
from fastapi import FastAPI, Request
import uvicorn
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

import pytest

from src.core.memory_otel import get_memory_otel, reset_memory_otel, memory_span
from src.core.memory_cloud import configure, status as cloud_status

app = FastAPI()
received_spans = []

@app.post("/v1/traces")
async def receive_traces(request: Request):
    data = await request.body()
    received_spans.append(data)
    return {"status": "ok"}

@app.get("/health")
async def health_check():
    return {"status": "up", "cloud": "superai-mock"}

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=4319, log_level="error")

@pytest.fixture(scope="module", autouse=True)
def mock_cloud_server():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1)
    yield

def test_live_otlp_collector_proof(monkeypatch):
    monkeypatch.setenv("SUPERAI_MEMORY_OTEL", "sdk")
    
    # Configure OpenTelemetry SDK manually for the test
    provider = TracerProvider()
    exporter = OTLPSpanExporter(endpoint="http://127.0.0.1:4319/v1/traces")
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    reset_memory_otel()
    otel = get_memory_otel()
    
    assert otel.mode == "sdk"
    
    with memory_span("test_live_otlp", attributes={"operation": "live_test"}):
        pass
    
    # Allow some time for export
    time.sleep(1)
    
    assert len(received_spans) > 0
    # verify the payload has our span
    found = False
    for payload in received_spans:
        if b"test_live_otlp" in payload:
            found = True
            break
    assert found

def test_live_cloud_health_proof(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPERAI_ALLOW_PRIVATE_URLS", "1")
    # Configure the cloud to point to our mock server
    monkeypatch.setenv("SUPERAI_MEMORY_CLOUD_CONFIG", str(tmp_path / "cloud_config.json"))
    
    configure(
        api_base="http://127.0.0.1:4319",
        dsn="postgresql://fake",
        enabled=True,
        region="local",
    )
    
    st = cloud_status()
    assert st["ok"] is True
    # The health probe in status should have hit the mock server
    assert st["reachable"] is True
    assert st["config"]["api_base"] == "http://127.0.0.1:4319"
