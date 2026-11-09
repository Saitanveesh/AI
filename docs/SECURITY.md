# Security model

## Explicitly unsupported

No actuator command, UAV flight-control command, weapon control, hostile-target classification, pursuit-path generation, or image-to-world geolocation.

## Threat model

- API is unauthenticated and therefore **loopback-only** by design. The CLI hardcodes host=127.0.0.1. Authenticated SSH forwarding is the supported remote access path.
- API offers only GET operations. There is no remote source selection, model upload, execution or settings mutation.
- Dashboard uses no external JavaScript/CSS, no tracking SDK, and inserts event strings via textContent rather than innerHTML.
- Privacy masks are applied **before** inference, display, and snapshots. Disable snapshots by default and obtain consent before recording.
- Source files, HEF files and label files are explicitly selected using environment variables, not uploaded through HTTP.
- Event logs may reveal camera operating times. Protect local storage and define retention.
- Reverse proxies or public bindings would change this threat model and are not supported without a separate security review.

## Known gaps

- No role-based authentication, TLS listener, signed artifacts, log rotation or encrypted-at-rest recordings.
- Python packages are version-ranged rather than fully hash-locked for each target OS/architecture.
- Hardware stack and accelerator adapter still need validation on the actual Pi.
- There is no secure boot or system attestation claim.

Do not advertise this as a certified or military-grade system until a separate threat model, independent review and qualification campaign are completed.
