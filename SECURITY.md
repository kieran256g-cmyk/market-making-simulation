# Security

This v1 runs locally without network access, credentials, third-party runtime
packages, dynamic plugins or serialized model loading. Keep credentials out of
this repository; `.env` files and generated results are ignored.

Generated files overwrite matching names in the chosen output directory. Use a
separate output directory for each experiment. CSV outputs contain generated
numeric values and ISO dates rather than arbitrary text supplied by a data feed.

Report a security issue through GitHub's private vulnerability reporting feature
if enabled; otherwise contact the repository owner privately before publishing
sensitive details. Do not include credentials in public issues.

