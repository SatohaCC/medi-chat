import pytest
from backend.config.origin_settings import read_allowed_origins


def test_local_urls_do_not_trust_vercel_names_outside_vercel():
    origins = read_allowed_origins({"VERCEL_URL": "untrusted.example"})
    assert "http://localhost:3000" in origins
    assert "https://untrusted.example" not in origins


def test_preview_and_production_origins_are_explicit_and_deduplicated():
    origins = read_allowed_origins(
        {
            "VERCEL": "1",
            "VERCEL_URL": "preview.vercel.app",
            "VERCEL_BRANCH_URL": "branch.vercel.app",
            "VERCEL_PROJECT_PRODUCTION_URL": "prod.vercel.app",
            "ALLOWED_ORIGINS": "https://custom.example, https://prod.vercel.app",
        }
    )
    assert origins == [
        "https://custom.example",
        "https://prod.vercel.app",
        "https://preview.vercel.app",
        "https://branch.vercel.app",
    ]
    assert "https://arbitrary.vercel.app" not in origins


def test_malformed_platform_hosts_are_not_added():
    assert (
        read_allowed_origins(
            {"VERCEL": "1", "VERCEL_URL": "https://bad.example", "ALLOWED_ORIGINS": ""}
        )
        == []
    )


@pytest.mark.parametrize(
    "deployment",
    [
        {"VERCEL": "1"},
        {"NODE_ENV": "production"},
        {"VERCEL": "1", "VERCEL_ENV": "preview"},
    ],
)
def test_deployments_do_not_default_to_localhost(deployment):
    assert read_allowed_origins(deployment) == []


def test_vercel_defaults_only_to_deployment_owned_urls():
    assert read_allowed_origins(
        {
            "VERCEL": "1",
            "VERCEL_URL": "preview.vercel.app",
            "VERCEL_PROJECT_PRODUCTION_URL": "prod.vercel.app",
            "VERCEL_BRANCH_URL": "branch.vercel.app",
        }
    ) == [
        "https://preview.vercel.app",
        "https://prod.vercel.app",
        "https://branch.vercel.app",
    ]


@pytest.mark.parametrize(
    "deployment", [{}, {"VERCEL": "1"}, {"NODE_ENV": "production"}]
)
@pytest.mark.parametrize(
    "explicit, expected",
    [
        ("", []),
        (" , ", []),
        (
            "http://localhost:3000, https://custom.example, http://localhost:3000",
            ["http://localhost:3000", "https://custom.example"],
        ),
    ],
)
def test_explicit_origins_are_respected_in_every_environment(
    deployment, explicit, expected
):
    assert read_allowed_origins({**deployment, "ALLOWED_ORIGINS": explicit}) == expected


def test_development_defaults_are_unchanged():
    assert read_allowed_origins({"NODE_ENV": "development"}) == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
