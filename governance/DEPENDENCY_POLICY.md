# DEPENDENCY_POLICY.md — Personal OS

Personal OS currently has **zero runtime dependencies** (stdlib only: `sqlite3`,
`http.server`, `smtplib`, `urllib`). This is a feature — keep it.

- Default answer to a new dependency is **no**. The bar: the stdlib alternative must be
  materially worse for correctness or safety, not merely less convenient.
- Any new package, lockfile, or `pyproject.toml` dependency change → **G7 + high-stakes**
  (RISK_REGISTER), regardless of package.
- A new dependency must arrive with a minimal exercised usage + test in the same packet, or
  it is auto-rejected.
- Pin exact versions. No postinstall scripts. License must be permissive (MIT/BSD/Apache-2).
- Model/API SDKs: rail adapters speak raw HTTPS to keep the surface auditable (the existing
  smoke clients already prove this pattern); vendor SDKs need a G6 design decision first.
