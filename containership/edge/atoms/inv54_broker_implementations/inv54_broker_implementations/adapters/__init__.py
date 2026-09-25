"""Provider adapters (components 13-17, 24, 25, 83).

Every adapter implements :class:`base.BrokerAdapter` and must pass
:func:`conformance.run_conformance`.  Provider client libraries are optional and imported
lazily; with no library installed, constructing an adapter raises INV54-E0903 rather than
pretending support.  Unit tests exercise each adapter's mapping/translation logic
against in-process fake clients; certification against real Kafka/RabbitMQ/SQS is
reported SKIPPED until run in a provisioned environment (tools/certify_providers.py).
"""
from .base import BrokerAdapter, Delivery, ReferenceLogAdapter, ReferenceQueueAdapter  # noqa: F401
from .conformance import run_conformance  # noqa: F401
