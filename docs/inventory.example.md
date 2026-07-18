# Private inventory template

Copy to `docs/private/inventory.md` (gitignored) and fill real values locally.
Never commit real LAN / Tailscale IPs, MAC addresses, or credentials.

## Windows compute node
- LAN IP: `<WINDOWS_LAN_IP>`
- Tailscale IP: `<WINDOWS_TAILSCALE_IP>`
- NIC MAC (WOL): `<WINDOWS_NIC_MAC>`

## Raspberry Pi (edge)
- Tailscale IP: `<PI_TAILSCALE_IP>`
- SSH: `pi@<PI_TAILSCALE_IP>` (from desktop)
- Roles: Tailscale gateway, WOL sender, **Web frontend host**
- Web root example: `/var/www/homellm`
- Deploy from desktop: `scripts/deploy-web-pi.ps1` + `.local/pi-deploy.env`
