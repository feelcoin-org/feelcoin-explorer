# Feelcoin Explorer — Verified RPC Failover Milestone

**Date:** 2026-10-09  
**Scope:** Explorer RPC backend resilience (not full website or VPS high availability)

## Architecture

```text
https://explorer.feelcoin.org
          |
    Explorer web process (Node 1)
          |
  Local read-only RPC failover proxy
     127.0.0.1:35790
       /         \
Primary RPC     Backup RPC
Node 1          SSH tunnel to Node 2
127.0.0.1:35781 127.0.0.1:35795 -> Node 2 loopback RPC
```

The SSH tunnel and proxy are supervised by systemd. The RPC proxy is bound to Node 1 loopback, not exposed as a public unrestricted daemon RPC endpoint.

## Verification record

These checks were completed from the Node 1 host during the October 9, 2026 deployment:

- The Node 2 managed SSH tunnel and failover proxy services were active.
- Both nodes agreed on the block hash at height **6400**: `65f49b8d4ace35fcf932d6be85b5e849939b9a70ed87f9cb9d4b11248bacb271`.
- Each backend successfully answered all five explorer RPC operations: `get_info`, `get_block`, `get_block_header_by_height`, `get_coinbase_tx_sum`, and `get_transactions`. The transaction test used a deliberately nonexistent hash to check endpoint response, rather than retrieval of an existing transaction.
- Isolated tests demonstrated simulated primary unavailability, backup selection, persisted trusted-height restoration, and primary failback.
- Isolated safety tests rejected missing or corrupted trusted state, a deliberately stale backup, and an incorrect checkpoint (HTTP 503).
- After the explorer was configured to use the proxy, `https://explorer.feelcoin.org/` returned HTTP 200 and both services were active.
- During a controlled production test, the proxy's primary RPC address was temporarily pointed to an unused port. The proxy successfully served Node 2 RPC data at height **6502**, while the public explorer root continued returning HTTP 200. The original primary configuration was restored and verified afterward.

## Protections and limitations

Current proxy implementation includes checkpoint verification, synchronized/online checks, trusted-height persistence, a five-block lag bound against its last trusted primary reference, and a retry of permitted read-only operations against a healthy backup.

**This is verified RPC-level failover only.** Explorer Nginx and the web application still run on Node 1. An outage of the entire Node 1 VPS or web stack is **not** covered by this milestone. HTTP 200 on the public root confirms reachability during the test, but does not constitute a comprehensive check of all dynamic pages. The trusted-height reference is not independently refreshed while the primary is unavailable; a long outage requires additional freshness monitoring. The initial test did not measure failover latency, nor demonstrate tunnel reconnection after a real network outage.

## Operational security

- Do not commit SSH private keys, production `authorized_keys`, passwords, tokens, private wallet materials, or internal host logs.
- The deployment code and systemd configuration are currently on the VPS. This document does **not** claim that those files were reviewed and published to GitHub.
- Before publishing production scripts, export and review them, remove environment-specific secrets, and provide a safe template configuration.

## Public links

- [Explorer](https://explorer.feelcoin.org/)
- [Feelcoin website](https://feelcoin.org/)
- [Feelcoin explorer repository](https://github.com/feelcoin-org/feelcoin-explorer)

*In Feels We Trust.*
