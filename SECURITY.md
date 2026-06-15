# Security

## Secrets

- **Never commit** `.env`, tokens, passwords, or API keys to this repository.
- Production secrets live only on the server (`~/HomeOS/.env` or equivalent), `chmod 600`.
- Use `.env.example` for documentation — placeholders only.

## If a secret was exposed

1. **Rotate immediately** (HA long-lived token, `SECRET_KEY`, DB password, app passcodes).
2. Update `.env` on the Pi and restart: `docker compose up -d`.
3. Do **not** paste tokens or passwords in GitHub issues, PRs, or chat logs you might publish.

## Home Assistant tokens

Create at **Profile → Security → Long-Lived Access Tokens**. Revoke old tokens after rotation.

Wire with:

```bash
./scripts/configure-ha-env.sh http://homeassistant:8123 'NEW_TOKEN_HERE'
```

## Remote access

- Prefer **Tailscale Serve** (tailnet-only HTTPS) over exposing port 80/8123 to the public internet.
- Set `COOKIE_SECURE=1` when serving the app over HTTPS.

## Reporting

This is a personal homelab project. If you find a security issue in the public repo, open a GitHub issue without including live credentials or home network details.

## Before every push (public repo)

One-time doc scrub is done — ongoing rule: **never commit `.env` or paste real tokens/IPs into tracked files.**

| Safe in git | Never in git |
|-------------|----------------|
| `.env.example` placeholders | `.env` |
| `192.168.x.x`, `<pi-lan-ip>` | Your real LAN IPs |
| `eyJ...` as docs example | Real JWT tokens |
| Generic hostnames | Tailscale FQDN, passwords |

If you add docs with your home IP by mistake, fix before push — you do not need to re-scrub the whole repo each time if you follow this habit.
