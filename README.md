# 🔎 Feelcoin Block Explorer

**Official open-source block explorer for the Feelcoin (FEEL) network.**

🌐 **Live explorer:** https://explorer.feelcoin.org

The Feelcoin Block Explorer is a public window into the Feelcoin blockchain. It allows miners, wallet users, developers and community members to inspect chain activity without operating their own local explorer interface.

## What you can explore

- **Blockchain progress:** current height, recent blocks and block timestamps.
- **Block lookup:** search by block height or block hash.
- **Transaction lookup:** search for a transaction hash and view publicly available chain information.
- **Network information:** difficulty, estimated network hashrate and connection indicators.
- **Mempool statistics:** view information about transactions awaiting inclusion when available.

The public explorer shows blockchain metadata. Feelcoin's privacy design means it should not be expected to reveal private wallet balances, recipients or confidential transaction amounts.

## Architecture

This repository contains the explorer application in [`explorer.py`](explorer.py), together with supporting documentation and [deployment resources](deployment/). The public explorer obtains blockchain information from Feelcoin node services.

Operators should keep internal daemon RPC endpoints private and expose the public interface through a controlled HTTPS reverse proxy.

## Availability and infrastructure

The production explorer is served at **https://explorer.feelcoin.org**. Deployment and high-availability work is documented in this repository where applicable; documented templates do not by themselves guarantee automatic failover is active in every deployment.

For current network data, consult the live explorer rather than treating example values or README snapshots as real-time information.

## Who is it for?

- **Miners:** check recent blocks and network conditions.
- **Wallet users:** verify a transaction hash and track inclusion in the blockchain.
- **Developers:** examine public chain information and troubleshoot integrations.
- **Community members:** independently inspect Feelcoin activity and network progress.

## Official Feelcoin ecosystem

| Resource | Link |
| --- | --- |
| Website | https://feelcoin.org |
| Blockchain | https://github.com/feelcoin-org/feelcoin |
| Mining pool | https://pool.feelcoin.org |
| Block explorer | https://explorer.feelcoin.org |
| Web wallet | https://wallet.feelcoin.org |
| Paper wallet | https://paper.feelcoin.org |
| Android wallet | https://github.com/feelcoin-org/feelcoin-android |
| Desktop wallet | https://github.com/feelcoin-org/feelcoin-desktop |

---

## In Feels We Trust

## Contact

Official Feelcoin support and project contact:

[**support@feelcoin.org**](mailto:support@feelcoin.org)

---

## Support Feelcoin Development

Feelcoin is an open-source project.

If you would like to support ongoing development, infrastructure, documentation, testing, and community services, voluntary donations are welcome.

### FEEL

```text
FBx9yk7huEF9PjR33zABbUj915wFVw3LeXfHSX4F7eXMgvyrkaV7tEW4gDwZ9rnQdnRQ4RmZsfPyNezu2jFoLewZLCuS8iM
```

### Bitcoin

Bitcoin mainnet:

```text
bc1q78zv45v3tfek730x8es88vjavj0qej2n766h2f
```

### Ethereum

Ethereum mainnet:

```text
0x7eFC0c47ab555041c79a7269a37f46A835EB466f
```

Donations are entirely voluntary and do not provide ownership, governance rights, guaranteed returns, or preferential treatment.

These voluntary donation addresses are separate from the consensus-enforced Feelcoin development treasury.
