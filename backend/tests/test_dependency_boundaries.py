"""本番パッケージの責務境界を、実際の有向importグラフで検証する。"""

import grimp
import pytest


@pytest.mark.parametrize(
    ("importer", "imported"),
    [
        ("backend.application.medicine", "backend.application.retrieval"),
        ("backend.infrastructure.persistence", "backend.infrastructure.sources"),
    ],
)
def test_consumers_do_not_depend_on_outer_read_adapters(importer, imported):
    graph = grimp.build_graph("backend", cache_dir=None)
    chains = graph.find_shortest_chains(
        importer=importer, imported=imported, as_packages=True
    )
    assert not chains, sorted(chains)
