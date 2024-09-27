#!/usr/bin/env python3
# Copyright 2024 dima.tisnek@canonical.com
# See LICENSE file for licensing details.

import asyncio
import logging
from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]
CHARM_CACHE = Path("/code/hexanator/.tox/integration/tmp/pytest/testm0/charms/hexanator_arm64.charm")


async def get_charm(ops_test):
    if CHARM_CACHE.exists():
        logging.warning("Reusing a charm from %r", CHARM_CACHE)
        return CHARM_CACHE
    rv = await ops_test.build_charm(".")
    logging.warning("Cached charm not found, made new one %r", rv)
    return rv


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    resources = {"gubernator": METADATA["resources"]["gubernator"]["upstream-source"]}
    charm = await get_charm(ops_test)

    # Deploy the charm and wait for active/idle status
    await asyncio.gather(
        ops_test.model.deploy(charm, resources=resources, application_name=APP_NAME),
        ops_test.model.wait_for_idle(
            apps=[APP_NAME], status="active", raise_on_blocked=True, timeout=1000
        ),
    )
