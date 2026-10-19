"""DB-side accident-detection fingerprint; never a security signature."""

PROJECTION_FINGERPRINT = """md5(
    COALESCE((SELECT jsonb_agg(to_jsonb(u) ORDER BY u.position,u.unit_id)::text
              FROM search_units u WHERE u.version_id=attachment_versions.version_id), '')
    || COALESCE((SELECT jsonb_agg(to_jsonb(p) ORDER BY p.yj_code,p.section_code)::text
                 FROM unit_products p WHERE p.version_id=attachment_versions.version_id), '')
)"""
