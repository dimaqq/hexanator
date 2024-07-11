from unittest.mock import ANY

import ops
import pytest
from scenario import Context, Container, Relation, State

from charm import HexanatorCharm

META = {
    "name": "hexanator",
    "requires": {
        "ingress": {
            "interface": "ingress"
        }
    },
    "containers": {
        "gubernator": {}
    },

}


def default_pebble_layer() -> dict:
    import yaml
    tmp = yaml.safe_load(open("rockcraft.yaml").read())
    assert tmp["services"]["gubernator"]["startup"] == "enabled"


def test_startup():
    ctx = Context(HexanatorCharm, meta=META)
    pebble_layers = {"default": ops.pebble.Layer(raw=default_pebble_layer())}
    container = Container(name="gubernator", can_connect=True, layers=pebble_layers)
    relation=Relation(endpoint="ingress", interface="ingress", remote_app_name="ingress")
    state = State( leader=True, relations=[relation], containers=[container])

    state = ctx.run(ctx.on.start(), state)
    state = ctx.run(ready_event := ctx.on.pebble_ready(container), state)
    state = ctx.run(ctx.on.relation_joined(relation), state)

    assert state.unit_status == ops.ActiveStatus()
    assert relation.local_app_data == {"model": ANY, "name": '"hexanator"', "port": "80", "strip-prefix": "true"}
    # FIXME: can't find anything useful to assert on...
    # - (ops.charm.PebbleReadyEvent).workload._pebble._service_status got updated on replan()
    # - but that bit of info seem lost, scenario.state._Event doesn't get updated
    # - getting mock _pebble out of state maybe?
    # assert ready_event.workload._pebble._service_status["gubernator"] == "active"
