# Private Access with Netcore

[Netcore](https://www.netcore.network/) creates encrypted peer-to-peer connections between devices using WireGuard. It lets trusted contacts access your self-hosted Still Here instance directly — no open ports, no public URL, no Cloudflare account.

## How it works

Once two devices are peered, they share a private WireGuard network. Your contacts can reach your Still Here app at your Netcore internal IP address (e.g. `http://10.x.x.x:8000/app`) as if they're on the same LAN — even if both machines are behind NAT on different networks.

This is not a tunnel (no public URL is created). It's **trusted-only private access** — only people you've explicitly peered with can connect.

## Setup on your server

```bash
# Download ncp2p for your OS from https://www.netcore.network/services
# Place binary in the netcore/ directory, then:

chmod +x netcore/ncp2p
./netcore-start.sh
```

`netcore-start.sh` handles initialization, WireGuard setup, and starts the client. It prints your internal IP when done.

Or manually:

```bash
cd netcore
./ncp2p initDb          # generates identity, assigns internal IP
sudo ./ncp2p setup $USER  # configures WireGuard (re-run after reboot)
./ncp2p                  # starts the client
```

The Netcore UI runs at `http://127.0.0.1:8080`.

## Sharing access with a contact

1. Open the Still Here app → **Settings** → **Private Access · Netcore**
2. Copy your peer identity JSON
3. Send it to your contact (Signal, email, etc.)
4. Your contact installs `ncp2p`, opens `http://127.0.0.1:8080`, goes to **Peer users → Add**, and pastes your JSON
5. They send you their peer identity JSON back
6. You add them the same way (or use the Settings UI)

Once both sides have added each other, your contact can open:

```
http://<your-internal-ip>:8000/portal   # family portal — live check-in status
http://<your-internal-ip>:8000/app      # full app
```

Your internal IP is shown in Settings → Private Access.

## Architecture

```
Your server
├── docker-compose  (Still Here on :8000)
└── ncp2p           (WireGuard mesh, e.g. 10.202.48.44)
        │
        │  encrypted peer-to-peer
        │
Contact's device
└── ncp2p → browser → http://10.202.48.44:8000/portal
```

The escalation chain (SMS, email, push) still works over the public internet. Netcore is only for human access — family portal, settings, monitoring.

## Notes

- Both machines need `ncp2p` running simultaneously for the connection to work
- The connection is direct — no traffic passes through Netcore's servers after peering
- Re-run `sudo ./ncp2p setup $USER` after each server reboot
