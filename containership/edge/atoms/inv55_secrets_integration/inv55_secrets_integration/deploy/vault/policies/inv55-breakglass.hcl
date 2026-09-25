# DRAFT break-glass policy: version destroy during incident response. Two-person activation required (INCIDENT_RESPONSE.md).
path "secret/destroy/TENANT/*" { capabilities = ["update"] }
