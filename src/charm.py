#!/usr/bin/env python3
# Copyright 2024 dima.tisnek@canonical.com
# See LICENSE file for licensing details.
"""Charmed Gubernator."""
import socket
from typing import TYPE_CHECKING, Any, Callable, Literal, Protocol, overload, reveal_type

import ops
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer


def kubernetes_service_dns_name():
    """Return the service DNS name for this application.

    This hostname is resolved to a set of ip addresses within the kubernetes cluster.
    Gubernator is designed so that any node can be called with any request, and it
    will handle the synchronisation internally.
    """
    pod_hostname = socket.getfqdn()
    _unit, service_dns_name = pod_hostname.split(".", 1)
    # FIXME: not sure about this, it could be customised by k8s admin
    assert service_dns_name.endswith(".local")
    return service_dns_name


class BoundEvent[T](ops.BoundEvent):
    """What BoundEvent will look like in future version of ops"""
    def __init__(self, emitter: ops.Object, event_type: T, event_kind: str): ...


class Framework(ops.Framework):
    """What Framework will look like in the future version of ops"""
    @overload
    def observe(self, bound_event: BoundEvent[ops.PebbleReadyEvent], observer: Callable[[ops.PebbleReadyEvent], None]): ...

    @overload
    def observe(self, bound_event: BoundEvent[ops.PebbleCustomNoticeEvent], observer: Callable[[ops.PebbleCustomNoticeEvent], None]): ...

    def observe(self, bound_event: ops.BoundEvent, observer: Callable[[Any], None]): ...


class ContainerEvents(Protocol):
    pebble_ready: BoundEvent[ops.BoundEvent]
    pebble_custom_notice: BoundEvent[ops.PebbleCustomNoticeEvent]
    pebble_check_failed: BoundEvent[ops.PebbleCheckFailedEvent]


class RelationEvents(Protocol):
    relation_created: BoundEvent[ops.RelationCreatedEvent]


class GeneratedB(Protocol):
    @overload
    # FIXME I'm not happy about the Literal here.
    # I'd rather have "something that equals 'gubernator'" to allow programmatic use
    def __getitem__(self, key: Literal["gubernator"]) -> ContainerEvents:
        ...

    @overload
    def __getitem__(self, key: Literal["rate-limit"]) -> RelationEvents:
        ...

    gubernator_pebble_ready: BoundEvent[ops.PebbleReadyEvent]
    rate_limit_relation_created: BoundEvent[ops.RelationCreatedEvent]

class LocalCharmEvents(GeneratedB, ops.CharmEvents): ...


class HexanatorCharm(ops.CharmBase):
    """Charm the service."""
    #on: MagicOn
    if TYPE_CHECKING:
        @property
        def on(self) -> LocalCharmEvents: ...

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self.ingress = IngressPerAppRequirer(self, port=80, strip_prefix=True)
        self.framework.observe(self.on["gubernator"].pebble_ready, self._on_pebble_ready)
        self.framework.observe(self.on["rate-limit"].relation_created, self._on_relation)

        reveal_type(self.on)
        reveal_type(self.on["gubernator"])
        reveal_type(self.on["gubernator"].pebble_ready)
        reveal_type(self.on["gubernator"].pebble_custom_notice)

        reveal_type(self.on["rate-limit"])
        reveal_type(self.on["rate-limit"].relation_created)

        reveal_type(self.on.gubernator_pebble_ready)
        reveal_type(self.on.rate_limit_relation_created)

    def _on_pebble_ready(self, event: ops.PebbleReadyEvent):
        """Kick off Pebble services.

        The `gubernator` service is configured and enabled in the `rockcraft.yaml` file.
        Pebble starts with `--on-hold` in the workload container, release it.
        """
        event.workload.replan()
        self.unit.status = ops.ActiveStatus()

    def _on_relation(self, event: ops.RelationCreatedEvent):
        """Publish the service DNS name to the rate limit user app."""
        if self.unit.is_leader():
            event.relation.data[self.app]["url"] = f"http://{kubernetes_service_dns_name()}/"


if __name__ == "__main__":  # pragma: nocover
    ops.main(HexanatorCharm)  # type: ignore
