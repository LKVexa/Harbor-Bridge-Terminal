# Compatibility policy (M28)

Every row of `matrix.json` is `tested`, `supported-untested` or `unsupported`. Only `tested` rows are claimed. Unsupported combinations must fail explicitly: the host refuses to start without TLS outside loopback, without an allowlisted digest, and the crypto layer refuses without `cryptography` rather than degrading.
