# Migration (INV-38-C095)

Migration behaviour across schema/backend/provider versions with rollback on
failure. Schema evolution follows the C022/C027 rules; recovery checkpoints carry
a `state_version` (`schemas/recovery-checkpoint-v1.schema.json`). **Status:**
`IN_PROGRESS`.
