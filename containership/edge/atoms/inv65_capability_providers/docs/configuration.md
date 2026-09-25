# Configuration (C033/C035)

Host config (`host.json`) is declarative; secure defaults: TLS required, residency default-deny, authz absence = deny, quotas on. Site/environment specifics (`site`, `region`, `environment`, residency policies, key files) live in config, so the immutable package is identical everywhere. Link configuration is validated before activation (schema + plain-data + no inline secrets + quotas + residency) and activated atomically with provenance (`config/model.py`).

Example keys: `contract_id, implementation_digest, provider_catalog, state_dir, state_keys{kid:file}, active_state_key, authn{issuer,audience,keys}, policy_keys{kid:file}, residency_policies[], backend, secret_backend, instance_id, site, region, environment, bind, port, tls{cert_file,key_file,client_ca_file}`.
