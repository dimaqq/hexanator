#!/usr/bin/env python3
# Copyright 2024 dima.tisnek@canonical.com
# See LICENSE file for licensing details.

import logging
import pathlib
import subprocess
from typing import Iterator

import jubilant
import pytest
import yaml

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(pathlib.Path("./charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]
IMAGE_NAME = METADATA["resources"]["gubernator"]["upstream-source"]


@pytest.fixture(scope="module")
def juju() -> Iterator[jubilant.Juju]:
    with jubilant.temp_model() as juju:
        yield juju


@pytest.fixture(scope="module")
def charm() -> pathlib.Path:
    subprocess.check_call(["charmcraft", "pack"])
    return next(pathlib.Path().glob("*.charm"))


@pytest.fixture(scope="module")
def gubernator_image() -> str:
    subprocess.check_call(["rockcraft", "pack"])
    rock = next(pathlib.Path().glob("*.rock"))
    subprocess.check_call(
        [
            "sudo",
            "ctr",
            "--namespace",
            "k8s.io",
            "images",
            "import",
            rock,
            "--base-name",
            IMAGE_NAME.split(":")[0],
        ]
    )
    return IMAGE_NAME


def test_build_and_deploy(juju: jubilant.Juju, charm: pathlib.Path, gubernator_image: str):
    """Build the charm-under-test and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    resources = {"gubernator": gubernator_image}
    juju.deploy(charm, app=APP_NAME, resources=resources)
    juju.wait(jubilant.all_active)
