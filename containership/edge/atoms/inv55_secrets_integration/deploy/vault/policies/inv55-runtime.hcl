# DRAFT least-privilege policy for the INV-55 runtime AppRole. Not applied anywhere.
# Replace TENANT with one policy per served tenant; do not use wildcards across tenants.
path "secret/data/TENANT/*"     { capabilities = ["read", "create", "update"] }
path "secret/metadata/TENANT/*" { capabilities = ["read", "list"] }
path "sys/leases/revoke"        { capabilities = ["update"] }
# Intentionally absent: secret/destroy/*, sys/*, auth/* (break-glass role only).
