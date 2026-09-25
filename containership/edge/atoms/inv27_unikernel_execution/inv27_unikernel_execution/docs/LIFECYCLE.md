# INV-27 instance lifecycle (generated from lifecycle.TRANSITIONS)

| From | Allowed next states |
|---|---|
| `pending` | `rejected`, `verified` |
| `verified` | `rejected`, `starting` |
| `starting` | `failed`, `running` |
| `running` | `failed`, `quarantined`, `stopping` |
| `quarantined` | `stopping` |
| `stopping` | `stopped` |
| `failed` | `stopped` |
| `rejected` | *(terminal)* |
| `stopped` | *(terminal)* |

Any other transition raises `UK_ILLEGAL_TRANSITION` and leaves state unchanged.
