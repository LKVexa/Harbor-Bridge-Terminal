# INV-31 Runtime Configuration

`FunctionPool` accepts three validated safety parameters at construction time:

| Parameter | Default | Constraint | Meaning |
|---|---:|---|---|
| `concurrency_limit` | 4 | positive integer | maximum simultaneously active invocation scopes per instance |
| `max_age` | 300 | positive integer | maximum reusable age in caller-supplied logical ticks |
| `max_instances` | 1024 | positive integer | hard in-process pool safety ceiling |

Invalid values fail before the pool becomes active. Instances created by a pool inherit its concurrency and age limits. Preloaded instances are rejected when their limits disagree with the pool configuration.

This is an in-process configuration surface, not yet a declarative configuration system. Provenance, signed configuration, transactional activation, environment overlays, and configuration rollback are listed as missing components in the post-audit report.
