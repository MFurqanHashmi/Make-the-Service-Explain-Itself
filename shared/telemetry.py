import logging
import os
import psutil
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.metrics import Observation
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_service_name = os.getenv("SERVICE_NAME", "unknown-service")
_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318").rstrip("/")
_interval = int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL_MS", "2000"))
_resource = Resource.create({
    "service.name": _service_name,
    "deployment.environment": "lab",
    "service.version": "1.0.0",
})

_metric_exporter = OTLPMetricExporter(endpoint=f"{_endpoint}/v1/metrics")
_metric_reader = PeriodicExportingMetricReader(_metric_exporter, export_interval_millis=_interval)
_metric_provider = MeterProvider(resource=_resource, metric_readers=[_metric_reader])
metrics.set_meter_provider(_metric_provider)
meter = metrics.get_meter("observability-lab", "1.0.0")

_trace_provider = TracerProvider(resource=_resource)
_trace_provider.add_span_processor(BatchSpanProcessor(
    OTLPSpanExporter(endpoint=f"{_endpoint}/v1/traces"),
    schedule_delay_millis=500,
    max_export_batch_size=128,
))
trace.set_tracer_provider(_trace_provider)
tracer = trace.get_tracer("observability-lab", "1.0.0")

_log_provider = LoggerProvider(resource=_resource)
_log_provider.add_log_record_processor(BatchLogRecordProcessor(
    OTLPLogExporter(endpoint=f"{_endpoint}/v1/logs"),
    schedule_delay_millis=500,
    max_export_batch_size=128,
))
set_logger_provider(_log_provider)
_root = logging.getLogger()
_root.setLevel(logging.INFO)
if not any(getattr(h, "_observability_lab", False) for h in _root.handlers):
    _handler = LoggingHandler(level=logging.INFO, logger_provider=_log_provider)
    _handler._observability_lab = True
    _root.addHandler(_handler)

HTTPXClientInstrumentor().instrument()

_readiness = meter.create_counter("lab.readiness", unit="{startup}")
_readiness.add(1, {"component": "application"})
with tracer.start_as_current_span("lab.readiness"):
    logging.getLogger("lab.readiness").info(
        "Telemetry pipeline readiness",
        extra={"event_name": "lab.readiness", "component": "application"},
    )

_process = psutil.Process()
def _cpu(_options):
    return [Observation(_process.cpu_percent(interval=None) / 100.0)]
def _memory(_options):
    return [Observation(_process.memory_info().rss, {"state": "rss"})]
meter.create_observable_gauge("process.cpu.utilization", callbacks=[_cpu], unit="1")
meter.create_observable_gauge("process.memory.usage", callbacks=[_memory], unit="By")
