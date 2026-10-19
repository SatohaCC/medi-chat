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
