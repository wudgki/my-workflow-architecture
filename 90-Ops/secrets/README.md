# secrets/ - Local Credentials Directory

**Every file in this directory is gitignored EXCEPT this README and `.gitkeep`
placeholders. Nothing in here ever leaves your local disk.**

This directory exists in every machine's local AI-Workspace, but is never
tracked, never synced, never published.

---

## Hard Rules (read before placing anything here)

1. **Never commit `.env`, API keys, OAuth tokens, private keys, mnemonics,
   wallet seeds, or session cookies.** If you can paste it once and lose
   money or access, it belongs here only.
2. **Never sync `secrets/` via Syncthing or any cloud drive (OneDrive /
   iCloud / Dropbox).** Cross-machine distribution must use SSH + `age` or
   `sops` over an encrypted channel, manually.
3. **Exchange API keys default to read-only permissions.** Trading,
   withdrawal, or transfer permissions are enabled per-strategy with an
   IP whitelist, never globally.
4. **Customer data, server SSH keys, and wallet private keys must never
   enter a public repository - including this blueprint.** Treat any commit
   that touches `secrets/<scope>/<file>` (other than this README) as an
   incident.
5. **If a secret is accidentally committed, rotate it immediately.**
   Rotation order:
   1. Revoke / regenerate the credential at the source (exchange / GitHub /
      cloud provider).
   2. Update the new value in `secrets/<scope>/`.
   3. Force-rotate any derived tokens, refresh tokens, or webhook URLs.
   4. Record the incident in `90-Ops/backup/secret-rotation-log.md`
      (private file, not committed).
   - Note: `git rm --cached` and `git push --force` do **not** un-leak a
     secret. The credential is already exposed the moment it lands on a
     remote. Rotation is the only fix.

---

## Recommended Layout

```
secrets/
  README.md                  <- this file (the only one tracked)
  shared/                    <- cross-phase shared (GitHub PAT, generic API keys)
  phase2/                    <- B2B platform (CMS admin, OAuth)
  phase3/                    <- crypto quant (exchange APIs, RPC endpoints)
  phase4/                    <- prediction market (Polymarket / Kalshi)
  hermes/                    <- Hermes service tokens, webhook secrets
  intel/                     <- intel pipelines (Discord / Telegram / Feishu)
```

Each subdirectory holds `.env` files, one per service.

---

## Naming Convention

`<service>.env`

Examples:
- `binance.env`
- `feishu-webhook.env`
- `github-pat.env`
- `polymarket.env`

Each `.env` file uses `KEY=value` syntax, one entry per line, no quotes
around values unless the value itself contains spaces.

---

## How Secrets Are Loaded at Runtime

| Environment | Mechanism |
|-------------|-----------|
| Local development (Windows / WSL) | `direnv` or `dotenv-cli` reads `secrets/<scope>/.env` and exports into the shell. |
| Hermes on VPS | `docker compose` reads `env_file:` directives, or systemd unit uses `EnvironmentFile=`. |
| Cross-machine (primary <-> secondary) | Manual transfer over SSH + `age` or `sops`. Never paste into chat or email. |
| CI / GitHub Actions (if ever used) | GitHub Secrets, never this directory. |

---

## Rotation Cadence

| Sensitivity | Examples | Max Age |
|-------------|----------|---------|
| Critical | Exchange trading keys, on-chain wallet keys | 90 days |
| High | OAuth refresh tokens, server SSH keys | 90 days |
| Medium | Notification webhooks, GitHub PAT | 180 days |
| Low | Read-only data API keys | 365 days |

Record every rotation in `90-Ops/backup/secret-rotation-log.md` (which
itself stays out of git).

---

## What Goes Here vs. Elsewhere

| Belongs in `secrets/` | Does NOT belong here |
|-----------------------|----------------------|
| `.env` with real values | `.env.example` (goes in code repo with placeholders) |
| Wallet private keys | Wallet addresses (those are public) |
| Exchange API keys | Strategy parameters |
| Server SSH private keys | `~/.ssh/known_hosts` |
| Customer PII exports | Anonymized samples for testing |
