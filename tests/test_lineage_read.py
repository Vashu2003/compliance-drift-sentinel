"""Slice 1 integration tests — run against a LIVE local DataHub (make up).

Verifies the client reads real lineage from the sample graph:
`fct_users_created` is built by an Airflow data job (its upstream).
"""
import pytest

from engine.datahub_client import DataHubClient, LineageNode

FCT_USERS_CREATED = "urn:li:dataset:(urn:li:dataPlatform:hive,fct_users_created,PROD)"


@pytest.mark.integration
async def test_search_returns_sample_datasets():
    async with DataHubClient().connect() as dh:
        urns = await dh.search_datasets()
    assert any("fct_users_created" in u for u in urns), urns


@pytest.mark.integration
async def test_upstreams_of_fct_users_created():
    async with DataHubClient().connect() as dh:
        nodes = await dh.upstreams(FCT_USERS_CREATED)

    assert nodes, "expected at least one upstream node"
    assert all(isinstance(n, LineageNode) for n in nodes)
    # Sample lineage: an Airflow data job constructs this table.
    assert any(n.entity_type == "DATA_JOB" for n in nodes), [n.urn for n in nodes]


@pytest.mark.integration
async def test_downstreams_direction_differs():
    async with DataHubClient().connect() as dh:
        ups = await dh.upstreams(FCT_USERS_CREATED)
        downs = await dh.downstreams(FCT_USERS_CREATED)
    # Direction flag must actually change the query result set.
    assert {n.urn for n in ups} != {n.urn for n in downs}
