# Security

The `ugclient-core` sidecar only listens on `127.0.0.1`, on a random port, and requires a one-time random token (passed from the Tauri shell to the UI) before any method other than `system.hello` is accepted. It refuses to bind non-loopback addresses.

Please report vulnerabilities privately via GitHub Security Advisories on this repository rather than a public issue.
