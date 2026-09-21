"""Packet loss testing.

Built on the same ping mechanism as :mod:`networkchecker.checks.ping`, but
tuned with a larger sample count for a statistically steadier loss
percentage. Note the honesty caveat below: ICMP echo only measures
combined round-trip loss. Separating upstream from downstream loss
requires a cooperating server at both ends (e.g. iperf3) and is tracked
as a future improvement — see documents/futureactions.md.
"""

from __future__ import annotations

from ..config import DEFAULT_PACKET_LOSS_TARGET
from ..models import PacketLossResult
from .ping import ping_host

DEFAULT_COUNT = 30

_NOTE = (
    "This is combined round-trip packet loss (upstream + downstream together). "
    "ICMP echo cannot isolate direction without a dual-ended tool such as iperf3; "
    "see documents/futureactions.md for planned directional loss testing."
)


def packet_loss_test(
    target: str = DEFAULT_PACKET_LOSS_TARGET,
    count: int = DEFAULT_COUNT,
    timeout_s: float = 1.5,
) -> PacketLossResult:
    result = ping_host(target=target, count=count, timeout_s=timeout_s)
    return PacketLossResult(
        target=target,
        packets_sent=result.sent,
        packets_received=result.received,
        loss_percent=result.loss_percent,
        note=_NOTE,
        error=result.error,
    )
