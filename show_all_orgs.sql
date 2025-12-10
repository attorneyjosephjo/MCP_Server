-- Show ALL organizations (including individual ones)

SELECT
    id,
    name,
    slug,
    tier,
    is_individual,
    primary_contact_email,
    is_active,
    created_at
FROM organizations
ORDER BY is_individual, created_at DESC;

-- Count organizations by type
SELECT
    CASE
        WHEN is_individual = true THEN 'Individual Users'
        ELSE 'Real Organizations'
    END as type,
    COUNT(*) as count
FROM organizations
WHERE is_active = true
GROUP BY is_individual;

-- Show which keys belong to which organization
SELECT
    o.name as org_name,
    o.slug as org_slug,
    o.is_individual,
    k.client_name as key_name,
    k.email as user_email,
    k.key_prefix
FROM organizations o
LEFT JOIN api_keys k ON k.organization_id = o.id
WHERE k.is_active = true
ORDER BY o.is_individual, o.name, k.created_at;
