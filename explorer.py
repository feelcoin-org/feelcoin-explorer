import time
#!/usr/bin/env python3

import json
import re
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

RPC = "http://127.0.0.1:35781"
HOST = "127.0.0.1"
PORT = 8081


def http_post(path, payload):
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        RPC + path,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def http_get(path):
    req = urllib.request.Request(RPC + path)

    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def rpc(method, params=None):
    return http_post(
        "/json_rpc",
        {
            "jsonrpc": "2.0",
            "id": "feelcoin-explorer",
            "method": method,
            "params": params or {}
        }
    )


def get_info():
    return http_get("/get_info")


# =========================================================
# FEELCOIN EMITTED SUPPLY
# =========================================================

ATOMIC_UNITS = 10 ** 12
SUPPLY_RPC_CHUNK = 1000

_supply_cache = {
    "height": 0,
    "emission_atomic": 0
}


def get_coinbase_tx_sum(height, count):
    return rpc(
        "get_coinbase_tx_sum",
        {
            "height": int(height),
            "count": int(count)
        }
    )


def get_emitted_supply(chain_height=None):
    """
    Return total protocol-issued FEEL through the current chain height.

    Uses emission_amount only.
    Transaction fees are excluded because they are not new supply.
    """

    if chain_height is None:
        chain_height = int(
            get_info().get("height", 0)
        )

    chain_height = int(chain_height)

    cached_height = int(
        _supply_cache.get("height", 0)
    )

    cached_emission = int(
        _supply_cache.get("emission_atomic", 0)
    )

    if cached_height > chain_height:
        cached_height = 0
        cached_emission = 0

    start = cached_height
    total = cached_emission

    while start < chain_height:

        count = min(
            SUPPLY_RPC_CHUNK,
            chain_height - start
        )

        result = get_coinbase_tx_sum(
            start,
            count
        ).get("result", {})

        status = result.get("status", "")

        if status != "OK":
            raise RuntimeError(
                "get_coinbase_tx_sum failed "
                f"at height {start}: {status}"
            )

        total += int(
            result.get(
                "emission_amount",
                0
            )
        )

        start += count

    _supply_cache["height"] = chain_height
    _supply_cache["emission_atomic"] = total

    return {
        "height": chain_height,
        "emitted_atomic": total,
        "emitted_supply":
            f"{total / ATOMIC_UNITS:.12f}",
        "ticker": "FEEL",
        "decimals": 12
    }


def get_block(height=None, block_hash=None):
    params = {}

    if height is not None:
        params["height"] = int(height)

    if block_hash:
        params["hash"] = block_hash

    return rpc("get_block", params)


def get_block_header(height):
    return rpc(
        "get_block_header_by_height",
        {"height": int(height)}
    )


def get_transactions(tx_hash):
    return http_post(
        "/get_transactions",
        {
            "txs_hashes": [tx_hash],
            "decode_as_json": True,
            "prune": False
        }
    )


def get_transactions_many(tx_hashes):
    if not tx_hashes:
        return {"txs": []}

    return http_post(
        "/get_transactions",
        {
            "txs_hashes": list(tx_hashes),
            "decode_as_json": True,
            "prune": False
        }
    )


def enrich_block_reward(result):
    """
    Add Feelcoin reward breakdown using the actual coinbase outputs.

    From height 590:
      vout[0] = miner / pool reward
      vout[1] = development treasury

    Transaction fees are summed from the block's normal transactions.
    """
    block_result = result.get("result", {})

    if not block_result:
        return result

    header = block_result.get("block_header", {})
    height = int(header.get("height", 0))
    total_reward = int(header.get("reward", 0))

    try:
        block_json = json.loads(block_result.get("json", "{}"))
    except Exception:
        block_json = {}

    miner_tx = block_json.get("miner_tx", {})
    vout = miner_tx.get("vout", [])

    miner_reward = 0
    treasury_reward = 0

    if len(vout) >= 1:
        miner_reward = int(vout[0].get("amount", 0))

    if height >= 590 and len(vout) >= 2:
        treasury_reward = int(vout[1].get("amount", 0))

    tx_fees = 0
    tx_hashes = block_result.get("tx_hashes", [])

    if tx_hashes:
        try:
            tx_data = get_transactions_many(tx_hashes)

            for tx in tx_data.get("txs", []):
                try:
                    tx_json = json.loads(tx.get("as_json", "{}"))
                except Exception:
                    tx_json = {}

                fee = 0

                rct = tx_json.get("rct_signatures", {})
                if isinstance(rct, dict):
                    fee = rct.get("txnFee", 0)

                if not fee:
                    fee = tx_json.get("fee", 0)

                try:
                    tx_fees += int(fee)
                except Exception:
                    pass

        except Exception:
            tx_fees = None

    block_result["reward_breakdown"] = {
        "total": total_reward,
        "miner": miner_reward,
        "treasury": treasury_reward,
        "fees": tx_fees,
        "activation_height": 590
    }

    return result


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#070b14">

<title>Feelcoin Explorer | FEEL Blockchain Explorer</title>

<link rel="icon" type="image/webp" href="/assets/feelcoin-coin.webp">
<link rel="apple-touch-icon" href="/assets/feelcoin-coin.webp">


<style>
:root{
  --bg:#070b14;
  --panel:#0d1422;
  --panel2:#111a2b;
  --line:#1d2a40;
  --text:#eef4ff;
  --muted:#8da0ba;
  --purple:#7c5cff;
  --green:#22d3a6;
  --red:#ff5f73;
}

*{box-sizing:border-box}

body{
  margin:0;
  min-height:100vh;
  color:var(--text);
  font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;

  background:
    linear-gradient(
      180deg,
      rgba(5,8,14,.78) 0%,
      rgba(5,8,14,.86) 55%,
      rgba(5,8,14,.92) 100%
    ),
    url("/assets/feelcoin-community.webp")
    center center / cover fixed no-repeat;
}

a{
  color:#a995ff;
  text-decoration:none;
}

button,input{
  font:inherit;
}

.shell{
  max-width:1400px;
  margin:auto;
  padding:22px;
}

header{
  position:relative;
  top:auto;
  z-index:20;

  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:20px;

  padding:16px 22px;

  background:rgba(13,20,34,.94);
  border:1px solid var(--line);
  border-radius:22px;

  backdrop-filter:blur(16px);
}

.brand{
  display:flex;
  align-items:center;
  gap:14px;
}

.logo{
  width:60px;
  height:60px;
  border-radius:50%;
  object-fit:cover;
  border:2px solid rgba(255,255,255,.22);
  box-shadow:0 0 28px rgba(124,92,255,.25);
}

.brand h1{
  margin:0;
  font-size:20px;
}

.brand p{
  margin:4px 0 0;
  color:var(--muted);
  font-size:12px;
}

nav{
  display:flex;
  gap:8px;
}

nav a{
  padding:9px 12px;
  color:#aab7c8;
  border-radius:10px;
}

nav a:hover{
  background:#172238;
  color:white;
}

.online{
  display:flex;
  align-items:center;
  gap:8px;
  font-size:13px;
}

.dot{
  width:9px;
  height:9px;
  border-radius:50%;
  background:var(--green);
  box-shadow:0 0 14px var(--green);
}

.hero{
  margin-top:20px;
  padding:34px;
  background:linear-gradient(180deg,rgba(17,26,43,.97),rgba(10,17,30,.97));
  border:1px solid var(--line);
  border-radius:20px;
}

.eyebrow{
  color:#a995ff;
  font-size:12px;
  font-weight:800;
  letter-spacing:.14em;
}

.hero h2{
  margin:12px 0 8px;
  font-size:38px;
}

.hero p{
  color:var(--muted);
}

.search{
  display:flex;
  gap:10px;
  margin-top:24px;
}

.search input{
  flex:1;
  padding:15px;
  color:white;
  background:#08101d;
  border:1px solid #293954;
  border-radius:12px;
  outline:none;
}

.search input:focus{
  border-color:var(--purple);
}

.search button,
.action{
  padding:0 22px;
  border:0;
  border-radius:12px;
  color:white;
  font-weight:800;
  cursor:pointer;
  background:linear-gradient(135deg,var(--purple),#6044dc);
}

.grid{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:14px;
  margin-top:18px;
}

.card{
  background:linear-gradient(180deg,rgba(17,26,43,.96),rgba(10,17,30,.96));
  border:1px solid var(--line);
  border-radius:17px;
}

.metric{
  padding:20px;
}

.label{
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:.08em;
  font-size:11px;
}

.big{
  margin-top:7px;
  font-size:27px;
  font-weight:900;
}

.sub{
  margin-top:6px;
  color:var(--muted);
  font-size:12px;
}

.section{
  margin-top:18px;
  padding:24px;
}

.section-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:15px;
  margin-bottom:18px;
}

.section h3{
  margin:0;
}

table{
  width:100%;
  border-collapse:collapse;
}

th,td{
  padding:13px 11px;
  text-align:left;
  border-bottom:1px solid var(--line);
  font-size:13px;
}

th{
  color:var(--muted);
  font-size:11px;
  text-transform:uppercase;
}

.hash{
  font-family:"Courier New",monospace;
}

.result{
  display:none;
}

.result.show{
  display:block;
}

.result-grid{
  display:grid;
  grid-template-columns:repeat(2,1fr);
  gap:12px;
}

.result-box{
  padding:16px;
  background:#08101d;
  border:1px solid var(--line);
  border-radius:14px;
  overflow-wrap:anywhere;
}

.result-box strong{
  display:block;
  margin-top:7px;
}

.raw{
  margin-top:16px;
  padding:16px;
  background:#050a12;
  border:1px solid var(--line);
  border-radius:14px;
  white-space:pre-wrap;
  word-break:break-word;
  font-family:"Courier New",monospace;
  font-size:12px;
  color:#c6d3e4;
  max-height:500px;
  overflow:auto;
}

footer{
  display:flex;
  justify-content:space-between;
  gap:15px;
  padding:28px 3px;
  color:var(--muted);
  font-size:12px;
}

@media(max-width:950px){
  .grid{
    grid-template-columns:repeat(2,1fr);
  }

  nav{
    display:flex;
    flex-wrap:wrap;
  }
}

@media(max-width:600px){
  .shell{
    padding:10px;
  }

  .logo{
    width:48px;
    height:48px;
  }

  .grid,
  .result-grid{
    grid-template-columns:1fr;
  }

  .hero{
    padding:22px;
  }

  .hero h2{
    font-size:29px;
  }

  .search{
    flex-direction:column;
  }

  .search button{
    padding:13px;
  }

  table{
    display:block;
    overflow-x:auto;
  }

  footer{
    flex-direction:column;
  }
}

/* Feelcoin community glass theme */
header,
.card,
.panel,
.search-box,
.result,
.stat,
.block-card,
.tx-card {
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

@media (max-width:720px){
  body{
    background-attachment:scroll;
  }
}


/* ===== FEELCOIN RESPONSIVE NAV FIX ===== */
@media (max-width: 950px) {
  header {
    flex-wrap: wrap;
    gap: 12px;
  }

  nav {
    display: flex !important;
    flex-wrap: wrap;
    width: 100%;
    order: 3;
    gap: 6px;
  }

  nav a {
    flex: 1 1 auto;
    text-align: center;
    white-space: nowrap;
  }

  .online {
    margin-left: auto;
  }
}

@media (max-width: 520px) {
  nav a {
    flex: 1 1 calc(50% - 6px);
  }
}



/* ===== FEELCOIN EXPLORER LIVE NETWORK ===== */

.feel-live-network{
  margin-top:18px;
}

.feel-live-network-card{
  padding:18px 20px;
  background:
    radial-gradient(
      circle at top right,
      rgba(124,92,255,.12),
      transparent 36%
    ),
    linear-gradient(
      180deg,
      rgba(17,26,43,.96),
      rgba(10,17,30,.96)
    );
  border:1px solid var(--line);
  border-radius:17px;
}

.feel-live-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:16px;
  margin-bottom:14px;
}

.feel-live-title{
  display:flex;
  align-items:center;
  gap:9px;
  font-size:12px;
  font-weight:900;
  text-transform:uppercase;
  letter-spacing:.10em;
}

.feel-live-master-dot,
.feel-node-dot{
  width:9px;
  height:9px;
  border-radius:50%;
  background:#738096;
  display:inline-block;
}

.feel-live-master-dot.online,
.feel-node-dot.online{
  background:var(--green);
  box-shadow:0 0 14px rgba(34,211,166,.65);
}

.feel-live-master-dot.warning,
.feel-node-dot.warning{
  background:#e6ab45;
  box-shadow:0 0 12px rgba(230,171,69,.35);
}

.feel-live-updated{
  color:var(--muted);
  font-size:11px;
  white-space:nowrap;
}

.feel-live-grid{
  display:grid;
  grid-template-columns:repeat(6,minmax(0,1fr));
  gap:10px;
}

.feel-live-item{
  min-width:0;
  padding:13px;
  background:#08101d;
  border:1px solid rgba(255,255,255,.055);
  border-radius:12px;
}

.feel-live-item .label{
  margin-bottom:6px;
}

.feel-live-value{
  font-size:15px;
  font-weight:850;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}

.feel-live-node{
  display:flex;
  align-items:center;
  gap:7px;
}

.feel-live-sub{
  margin-top:5px;
  color:var(--muted);
  font-size:10px;
}

@media(max-width:1000px){
  .feel-live-grid{
    grid-template-columns:repeat(3,minmax(0,1fr));
  }
}

@media(max-width:600px){
  .feel-live-head{
    flex-direction:column;
    align-items:flex-start;
    gap:5px;
  }

  .feel-live-grid{
    grid-template-columns:repeat(2,minmax(0,1fr));
  }

  .feel-live-network-card{
    padding:16px;
  }
}

/* ===== END FEELCOIN EXPLORER LIVE NETWORK ===== */



/* ===== FEELCOIN FULL GLASS THEME ===== */

header{
  background:rgba(13,20,34,.72) !important;
  border:1px solid rgba(255,255,255,.08) !important;

  backdrop-filter:blur(16px) saturate(115%) !important;
  -webkit-backdrop-filter:blur(16px) saturate(115%) !important;

  box-shadow:
    0 10px 35px rgba(0,0,0,.18),
    inset 0 1px 0 rgba(255,255,255,.035);
}


.hero{
  background:
    linear-gradient(
      180deg,
      rgba(17,26,43,.70),
      rgba(10,17,30,.64)
    ) !important;

  border:1px solid rgba(255,255,255,.08) !important;

  backdrop-filter:blur(15px) saturate(115%) !important;
  -webkit-backdrop-filter:blur(15px) saturate(115%) !important;

  box-shadow:
    0 12px 35px rgba(0,0,0,.18),
    inset 0 1px 0 rgba(255,255,255,.025);
}


.card{
  background:
    linear-gradient(
      180deg,
      rgba(17,26,43,.68),
      rgba(10,17,30,.62)
    ) !important;

  border:1px solid rgba(255,255,255,.075) !important;

  backdrop-filter:blur(14px) saturate(110%) !important;
  -webkit-backdrop-filter:blur(14px) saturate(110%) !important;

  box-shadow:
    0 10px 30px rgba(0,0,0,.16),
    inset 0 1px 0 rgba(255,255,255,.025);
}


.metric{
  background:
    linear-gradient(
      180deg,
      rgba(17,26,43,.63),
      rgba(10,17,30,.57)
    ) !important;
}


.section{
  background:
    linear-gradient(
      180deg,
      rgba(17,26,43,.66),
      rgba(10,17,30,.60)
    ) !important;
}


.search input{
  background:rgba(8,16,29,.56) !important;
  border:1px solid rgba(255,255,255,.09) !important;

  backdrop-filter:blur(8px) !important;
  -webkit-backdrop-filter:blur(8px) !important;

  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.02);
}


.result-box{
  background:rgba(8,16,29,.55) !important;
  border:1px solid rgba(255,255,255,.07) !important;

  backdrop-filter:blur(9px) !important;
  -webkit-backdrop-filter:blur(9px) !important;
}


.raw{
  background:rgba(5,10,18,.60) !important;
  border:1px solid rgba(255,255,255,.07) !important;

  backdrop-filter:blur(8px) !important;
  -webkit-backdrop-filter:blur(8px) !important;
}


.feel-live-network-card{
  background:
    linear-gradient(
      180deg,
      rgba(17,26,43,.68),
      rgba(10,17,30,.62)
    ) !important;

  border:1px solid rgba(255,255,255,.075) !important;

  backdrop-filter:blur(14px) saturate(110%) !important;
  -webkit-backdrop-filter:blur(14px) saturate(110%) !important;

  box-shadow:
    0 10px 30px rgba(0,0,0,.16),
    inset 0 1px 0 rgba(255,255,255,.025);
}


.feel-live-item{
  background:rgba(8,16,29,.52) !important;
  border:1px solid rgba(255,255,255,.055) !important;

  backdrop-filter:blur(8px) !important;
  -webkit-backdrop-filter:blur(8px) !important;
}


table{
  background:transparent !important;
}


th,
td{
  background:transparent !important;
}


footer{
  background:rgba(8,14,24,.34);
  border:1px solid rgba(255,255,255,.045);
  border-radius:14px;

  padding:18px 20px !important;
  margin-top:18px;

  backdrop-filter:blur(10px);
  -webkit-backdrop-filter:blur(10px);
}


/* Slightly brighten text on glass surfaces */

.label,
.sub{
  text-shadow:0 1px 2px rgba(0,0,0,.35);
}


.big,
.feel-live-value{
  text-shadow:0 2px 5px rgba(0,0,0,.35);
}


/* ===== END FEELCOIN FULL GLASS THEME ===== */



/* Hide legacy footer refresh timestamp */
#updated{
  display:none !important;
}

</style>

<!-- FEELCOIN EXPLORER SEO START -->

<meta name="description"
content="Official Feelcoin blockchain explorer. Inspect FEEL blocks, transactions, network difficulty, rewards, treasury allocations and live blockchain activity.">

<meta name="keywords"
content="Feelcoin, FEEL, cryptocurrency, blockchain, RandomX, Proof of Work, CPU mining, crypto wallet, mining pool, blockchain explorer, non-custodial wallet, open source cryptocurrency">

<meta name="robots"
content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">

<meta name="author" content="feelcoin-dev">

<link rel="canonical" href="https://explorer.feelcoin.org/">

<meta property="og:type" content="website">
<meta property="og:site_name" content="Feelcoin">
<meta property="og:title" content="Feelcoin Explorer | FEEL Blockchain Explorer">
<meta property="og:description" content="Official Feelcoin blockchain explorer. Inspect FEEL blocks, transactions, network difficulty, rewards, treasury allocations and live blockchain activity.">
<meta property="og:url" content="https://explorer.feelcoin.org/">
<meta property="og:image" content="https://feelcoin.org/assets/feelcoin-coin.webp">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@feelcoin_org">
<meta name="twitter:title" content="Feelcoin Explorer | FEEL Blockchain Explorer">
<meta name="twitter:description" content="Official Feelcoin blockchain explorer. Inspect FEEL blocks, transactions, network difficulty, rewards, treasury allocations and live blockchain activity.">
<meta name="twitter:image" content="https://feelcoin.org/assets/feelcoin-coin.webp">

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Feelcoin Explorer",
  "url": "https://explorer.feelcoin.org/",
  "description": "Official Feelcoin blockchain explorer. Inspect FEEL blocks, transactions, network difficulty, rewards, treasury allocations and live blockchain activity.",
  "isPartOf": {
    "@type": "WebSite",
    "name": "Feelcoin",
    "url": "https://feelcoin.org/"
  },
  "sameAs": [
    "https://github.com/feelcoin-org",
    "https://x.com/feelcoin_org",
    "https://discord.com/invite/2sx7Q8yAR"
  ]
}
</script>

<!-- FEELCOIN EXPLORER SEO END -->

</head>

<body>

<div class="shell">

<header>

<div class="brand">
<img
  src="https://i.imgur.com/VPorAY4.jpeg"
  class="logo"
  alt="Feelcoin">

<div>
<h1>Feelcoin Explorer</h1>
<p>Official Blockchain Explorer</p>
</div>
</div>

<nav>
<a href="/">Explorer</a>
<a href="https://feelcoin.org" target="_blank" rel="noopener noreferrer">Website</a>
<a href="https://pool.feelcoin.org" target="_blank" rel="noopener noreferrer">Mining Pool</a>
</nav>

<div class="online">
<span class="dot" id="statusDot"></span>
<span id="status">Connected</span>
</div>

</header>


<section class="hero">

<div class="eyebrow">FEELCOIN BLOCKCHAIN</div>

<h2>Explore the Feelcoin Network</h2>

<p>
Search block heights, block hashes and transaction hashes while monitoring live network statistics.
</p>

<div class="search">
<input
  id="searchBox"
  placeholder="Block height, block hash or transaction hash">

<button onclick="searchChain()">
Search
</button>
</div>

</section>


<section class="grid">

<div class="card metric">
<div class="label">Blockchain Height</div>
<div class="big" id="height">—</div>
<div class="sub">Current chain</div>
</div>

<div class="card metric">
<div class="label">Difficulty</div>
<div class="big" id="difficulty">—</div>
<div class="sub">Network difficulty</div>
</div>

<div class="card metric">
<div class="label">Estimated Hashrate</div>
<div class="big" id="hashrate">—</div>
<div class="sub">Difficulty / target time</div>
</div>

<div class="card metric">
<div class="label">Confirmed Transactions</div>
<div class="big" id="txcount">—</div>
<div class="sub">Blockchain transactions</div>
</div>

<div class="card metric">
<div class="label">Mempool</div>
<div class="big" id="mempool">—</div>
<div class="sub">Pending transactions</div>
</div>

<div class="card metric">
<div class="label">Connections</div>
<div class="big" id="connections">—</div>
<div class="sub">Incoming + outgoing</div>
</div>

<div class="card metric">
<div class="label">Block Target</div>
<div class="big" id="target">—</div>
<div class="sub">Seconds</div>
</div>

<div class="card metric">
<div class="label">Network</div>
<div class="big" id="network">—</div>
<div class="sub">Feelcoin network</div>
</div>

<div class="card metric">
<div class="label">Emitted Supply</div>
<div class="big" id="emittedSupply">—</div>
<div class="sub">Total FEEL created by protocol</div>
</div>

</section>

<section
  class="feel-live-network"
  id="feelExplorerNetworkStatus">

<div class="feel-live-network-card">

<div class="feel-live-head">

<div class="feel-live-title">
<span
  class="feel-live-master-dot"
  id="feelExplorerMasterDot"></span>
<span>Live Network Infrastructure</span>
</div>

<div
  class="feel-live-updated"
  id="feelExplorerUpdated">
Checking network...
</div>

</div>


<div class="feel-live-grid">


<div class="feel-live-item">
<div class="label">Network Tip</div>
<div
  class="feel-live-value"
  id="feelExplorerHeight">—</div>
<div class="feel-live-sub">
Current mainnet height
</div>
</div>


<div class="feel-live-item">
<div class="label">Block Target</div>
<div
  class="feel-live-value"
  id="feelExplorerTarget">120s</div>
<div class="feel-live-sub">
Protocol target
</div>
</div>


<div class="feel-live-item">
<div class="label">Node 1</div>

<div class="feel-live-value feel-live-node">
<span
  class="feel-node-dot"
  id="feelExplorerNode1Dot"></span>

<span id="feelExplorerNode1Status">
Checking
</span>
</div>

<div
  class="feel-live-sub"
  id="feelExplorerNode1Height">
node1.feelcoin.org
</div>
</div>


<div class="feel-live-item">
<div class="label">Node 2</div>

<div class="feel-live-value feel-live-node">
<span
  class="feel-node-dot"
  id="feelExplorerNode2Dot"></span>

<span id="feelExplorerNode2Status">
Checking
</span>
</div>

<div
  class="feel-live-sub"
  id="feelExplorerNode2Height">
node2.feelcoin.org
</div>
</div>


<div class="feel-live-item">
<div class="label">Synchronization</div>

<div
  class="feel-live-value"
  id="feelExplorerSync">
Checking
</div>

<div class="feel-live-sub">
Network consensus health
</div>
</div>


<div class="feel-live-item">
<div class="label">Infrastructure</div>

<div
  class="feel-live-value"
  id="feelExplorerInfrastructure">
Checking
</div>

<div class="feel-live-sub">
Published bootstrap nodes
</div>
</div>


</div>

</div>

</section>



<section class="card section">

<div class="section-head">
<h3>Latest Blocks</h3>
<span class="sub">Live from feelcoind</span>
</div>

<table>

<thead>
<tr>
<th>Height</th>
<th>Age</th>
<th>Hash</th>
<th>Txs</th>
<th>Difficulty</th>
<th>Reward</th>
</tr>
</thead>

<tbody id="blocks">
<tr>
<td colspan="6">Loading...</td>
</tr>
</tbody>

</table>

</section>


<section class="card section result" id="resultBox">

<div class="section-head">
<h3 id="resultTitle">Search Result</h3>

<button class="action" onclick="closeResult()">
Close
</button>
</div>

<div id="resultDetails"></div>

<details style="margin-top:18px">
<summary style="cursor:pointer;color:#a995ff">
Raw RPC response
</summary>

<div class="raw" id="rawResult"></div>
</details>

</section>


<footer>

<span>
© <span id="year"></span> Feelcoin Network • In Feels We Trust
</span>

<span id="updated">
Loading...
</span>

</footer>

</div>


<script>

const $ = id => document.getElementById(id);

$("year").textContent = new Date().getFullYear();


function number(n){
  return Number(n || 0).toLocaleString();
}
function feel(value){
  const n = Number(value || 0);
  return (n / 1_000_000_000_000).toFixed(12) + " FEEL";
}

function hashRate(h){
  h = Number(h || 0);

  if(h < 1e3)
    return h.toFixed(0) + " H/s";

  if(h < 1e6)
    return (h / 1e3).toFixed(2) + " KH/s";

  if(h < 1e9)
    return (h / 1e6).toFixed(2) + " MH/s";

  if(h < 1e12)
    return (h / 1e9).toFixed(2) + " GH/s";

  return (h / 1e12).toFixed(2) + " TH/s";
}


let serverTimeOffset = 0;

function age(ts){
  const now =
    Date.now() / 1000 +
    serverTimeOffset;

  const diff = Math.max(
    0,
    now - Number(ts || 0)
  );

  if(diff < 60)
    return Math.floor(diff) + " sec";

  if(diff < 3600)
    return Math.floor(diff / 60) + " min";

  if(diff < 86400)
    return Math.floor(diff / 3600) + " hr";

  return Math.floor(diff / 86400) + " days";
}


function shortHash(h){
  if(!h)
    return "—";

  return h.slice(0,12) + "…" + h.slice(-10);
}


function resultBox(label,value){
  return `
    <div class="result-box">
      <div class="label">${label}</div>
      <strong>${value ?? "—"}</strong>
    </div>
  `;
}




function setExplorerNode(prefix,node){

  const dot =
    $(prefix + "Dot");

  const status =
    $(prefix + "Status");

  const detail =
    $(prefix + "Height");

  if(!dot || !status || !detail)
    return;

  dot.classList.remove(
    "online",
    "warning"
  );

  if(node && node.online){

    dot.classList.add("online");

    status.textContent =
      node.synchronized === false
        ? "Syncing"
        : "Online";

    detail.textContent =
      node.height !== undefined
        ? "Height " +
          Number(node.height).toLocaleString()
        : (node.host || "Online");

  }
  else{

    dot.classList.add("warning");

    status.textContent =
      "Offline";

    detail.textContent =
      node && node.host
        ? node.host
        : "Unavailable";

  }

}


async function loadExplorerNetworkStatus(){

  const masterDot =
    $("feelExplorerMasterDot");

  try{

    const response =
      await fetch(
        "/network-status.json",
        {cache:"no-store"}
      );

    if(!response.ok)
      throw new Error(
        "HTTP " + response.status
      );

    const data =
      await response.json();

    const network =
      data.network || {};

    const nodes =
      data.nodes || {};

    $("feelExplorerHeight").textContent =
      network.height !== undefined
        ? Number(
            network.height
          ).toLocaleString()
        : "—";

    $("feelExplorerTarget").textContent =
      network.target_seconds !== undefined
        ? network.target_seconds + "s"
        : "120s";


    setExplorerNode(
      "feelExplorerNode1",
      nodes.node1
    );

    setExplorerNode(
      "feelExplorerNode2",
      nodes.node2
    );


    const node1Online =
      !!(
        nodes.node1 &&
        nodes.node1.online
      );

    const node2Online =
      !!(
        nodes.node2 &&
        nodes.node2.online
      );

    const bothOnline =
      node1Online &&
      node2Online;


    const node1Synced =
      !nodes.node1 ||
      nodes.node1.synchronized !== false;

    const node2Synced =
      !nodes.node2 ||
      nodes.node2.synchronized !== false;

    const networkSynced =
      network.synchronized !== false &&
      node1Synced &&
      node2Synced;


    $("feelExplorerSync").textContent =
      networkSynced
        ? "Synchronized"
        : "Syncing";


    $("feelExplorerInfrastructure").textContent =
      bothOnline
        ? "Operational"
        : (
            node1Online ||
            node2Online
              ? "Degraded"
              : "Unavailable"
          );


    masterDot.classList.remove(
      "online",
      "warning"
    );

    masterDot.classList.add(
      bothOnline && networkSynced
        ? "online"
        : "warning"
    );


    if(data.updated_at){

      const updated =
        new Date(
          data.updated_at
        );

      const ageMs =
        Date.now() -
        updated.getTime();

      if(ageMs > 120000){

        $("feelExplorerUpdated")
          .textContent =
          "Status delayed • " +
          updated.toLocaleTimeString();

        masterDot.classList.remove(
          "online"
        );

        masterDot.classList.add(
          "warning"
        );

      }
      else{

        $("feelExplorerUpdated")
          .textContent =
          "Updated " +
          updated.toLocaleTimeString();

      }

    }
    else{

      $("feelExplorerUpdated")
        .textContent =
        "Live network status";

    }

  }
  catch(error){

    masterDot.classList.remove(
      "online"
    );

    masterDot.classList.add(
      "warning"
    );

    $("feelExplorerSync").textContent =
      "Unavailable";

    $("feelExplorerInfrastructure")
      .textContent =
      "Unavailable";

    $("feelExplorerUpdated")
      .textContent =
      "Network status unavailable";

    console.warn(
      "Feelcoin network status:",
      error
    );

  }

}


async function loadHome(){

  try{

    const response = await fetch(
      "/api/home",
      {cache:"no-store"}
    );

    if(!response.ok)
      throw new Error("HTTP " + response.status);

    const data = await response.json();
    const info = data.info;

    if(data.server_time){
      serverTimeOffset =
        Number(data.server_time) -
        Date.now() / 1000;
    }

    $("height").textContent =
      number(info.height);

    $("difficulty").textContent =
      number(info.difficulty);

    $("target").textContent =
      number(info.target);

    $("hashrate").textContent =
      hashRate(
        Number(info.difficulty) /
        Number(info.target || 120)
      );

    $("txcount").textContent =
      number(info.tx_count);

    $("mempool").textContent =
      number(info.tx_pool_size);

    $("connections").textContent =
      number(
        Number(info.incoming_connections_count || 0) +
        Number(info.outgoing_connections_count || 0)
      );

    $("network").textContent =
      info.nettype || "mainnet";

    if(data.supply && data.supply.emitted_supply){

      $("emittedSupply").textContent =
        Number(
          data.supply.emitted_supply
        ).toLocaleString(
          undefined,
          {
            minimumFractionDigits: 2,
            maximumFractionDigits: 6
          }
        ) + " FEEL";

    }else{

      $("emittedSupply").textContent = "—";

    }

    $("blocks").innerHTML = "";

    for(const b of data.blocks){

      const row = document.createElement("tr");

      row.innerHTML = `
        <td>
          <a href="#" onclick="searchValue('${b.height}');return false;">
            ${b.height}
          </a>
        </td>

        <td>
          ${age(b.timestamp)}
        </td>

        <td class="hash">
          <a href="#" onclick="searchValue('${b.hash}');return false;">
            ${shortHash(b.hash)}
          </a>
        </td>

        <td>
          ${number(b.num_txes)}
        </td>

        <td>
          ${number(b.difficulty)}
        </td>

        <td>
         ${feel(b.reward)}
        </td>
      `;

      $("blocks").appendChild(row);
    }

    $("status").textContent =
      "Connected";

    $("statusDot").style.background =
      "var(--green)";

    $("updated").textContent =
      "Updated " +
      new Date().toLocaleTimeString();

  }
  catch(error){

    $("status").textContent =
      "RPC Offline";

    $("statusDot").style.background =
      "var(--red)";

    $("updated").textContent =
      "Unable to reach daemon";

  }

}


async function searchValue(value){

  $("searchBox").value = value;
  await searchChain();

}


function renderBlock(data){

  const result = data.data.result || {};
  const header = result.block_header || {};
  const rewards = result.reward_breakdown || {};

  const rewardDetails =
    Number(header.height) >= 590
      ? `
        ${resultBox("Total Reward",feel(rewards.total ?? header.reward))}
        ${resultBox("Miner / Pool Reward",feel(rewards.miner))}
        ${resultBox("Development Treasury",feel(rewards.treasury))}
        ${resultBox(
          "Transaction Fees",
          rewards.fees === null || rewards.fees === undefined
            ? "Unavailable"
            : feel(rewards.fees)
        )}
      `
      : `${resultBox("Reward",feel(header.reward))}`;

  $("resultDetails").innerHTML = `
    <div class="result-grid">

      ${resultBox("Height",header.height)}
      ${resultBox("Hash",header.hash)}
      ${resultBox("Previous Hash",header.prev_hash)}
      ${resultBox("Timestamp",header.timestamp)}
      ${resultBox("Age",age(header.timestamp))}
      ${resultBox("Difficulty",number(header.difficulty))}
      ${rewardDetails}
      ${resultBox("Transactions",number(header.num_txes))}
      ${resultBox("Block Size",number(header.block_size))}
      ${resultBox("Block Weight",number(header.block_weight))}
      ${resultBox("Nonce",header.nonce)}
      ${resultBox("Major Version",header.major_version)}

    </div>
  `;

}


function renderTransaction(data){

  const tx =
    data.data.txs &&
    data.data.txs.length
      ? data.data.txs[0]
      : {};

  $("resultDetails").innerHTML = `
    <div class="result-grid">

      ${resultBox("Transaction Hash",tx.tx_hash || data.query)}
      ${resultBox("In Pool",String(tx.in_pool ?? false))}
      ${resultBox("Block Height",tx.block_height ?? "—")}
      ${resultBox("Block Timestamp",tx.block_timestamp ?? "—")}
      ${resultBox("Double Spend Seen",String(tx.double_spend_seen ?? false))}
      ${resultBox("Prunable Hash",tx.prunable_hash || "—")}

    </div>
  `;

}


async function searchChain(){

  const query =
    $("searchBox")
    .value
    .trim();

  if(!query)
    return;

  $("resultBox")
    .classList
    .add("show");

  $("resultTitle").textContent =
    "Searching...";

  $("resultDetails").innerHTML =
    "<div class='sub'>Loading...</div>";

  $("rawResult").textContent =
    "";

  try{

    const response = await fetch(
      "/api/search?q=" +
      encodeURIComponent(query),
      {cache:"no-store"}
    );

    const data = await response.json();

    if(!response.ok)
      throw new Error(
        data.error || "Search failed"
      );

    $("resultTitle").textContent =
      data.type === "transaction"
        ? "Transaction Details"
        : "Block Details";

    if(
      data.type === "block-height" ||
      data.type === "block-hash"
    ){
      renderBlock(data);
    }
    else if(data.type === "transaction"){
      renderTransaction(data);
    }

    $("rawResult").textContent =
      JSON.stringify(
        data,
        null,
        2
      );

    $("resultBox")
      .scrollIntoView({
        behavior:"smooth",
        block:"start"
      });

  }
  catch(error){

    $("resultTitle").textContent =
      "Not Found";

    $("resultDetails").innerHTML =
      `<div class="result-box">
         ${error.message}
       </div>`;

  }

}


function closeResult(){

  $("resultBox")
    .classList
    .remove("show");

}


$("searchBox")
.addEventListener(
  "keydown",
  function(event){

    if(event.key === "Enter")
      searchChain();

  }
);


loadHome();

setInterval(
  loadHome,
  30000
);



loadExplorerNetworkStatus();

setInterval(
  loadExplorerNetworkStatus,
  30000
);

</script>

</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.send_header(
            "Cache-Control",
            "no-store"
        )
        self.end_headers()
        self.wfile.write(body)


    def send_html(self):
        body = HTML.encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.send_header(
            "Cache-Control",
            "no-store"
        )
        self.end_headers()
        self.wfile.write(body)


    def do_GET(self):
        parsed = urlparse(self.path)

        try:

            if parsed.path == "/":
                return self.send_html()


            if parsed.path == "/api/supply":

                info = get_info()

                height = int(
                    info.get("height", 0)
                )

                return self.send_json(
                    get_emitted_supply(
                        height
                    )
                )


            if parsed.path == "/api/home":

                info = get_info()

                height = int(
                    info.get("height", 0)
                )

                supply = get_emitted_supply(
                    height
                )

                blocks = []

                top_height = max(
                    0,
                    height - 1
                )

                bottom_height = max(
                    -1,
                    height - 11
                )

                for h in range(
                    top_height,
                    bottom_height,
                    -1
                ):
                    try:
                        result = get_block_header(h)

                        header = (
                            result
                            .get("result", {})
                            .get("block_header", {})
                        )

                        if header:
                            blocks.append(header)

                    except Exception:
                        pass

                return self.send_json(
                    {
                        "info": info,
                        "supply": supply,
                        "blocks": blocks,
                        "server_time": int(time.time())
                    }
                )


            if parsed.path == "/api/search":

                query = (
                    parse_qs(parsed.query)
                    .get("q", [""])[0]
                    .strip()
                )

                if not query:
                    return self.send_json(
                        {"error": "Empty query"},
                        400
                    )


                if query.isdigit():

                    result = get_block(
                        height=int(query)
                    )

                    if not result.get("result"):
                        return self.send_json(
                            {
                                "error":
                                "Block not found",
                                "query":
                                query
                            },
                            404
                        )

                    result = enrich_block_reward(result)

                    return self.send_json(
                        {
                            "type":
                            "block-height",
                            "query":
                            query,
                            "data":
                            result
                        }
                    )


                if re.fullmatch(
                    r"[0-9a-fA-F]{64}",
                    query
                ):

                    try:
                        block = get_block(
                            block_hash=query
                        )

                        block_result = (
                            block.get(
                                "result",
                                {}
                            )
                        )

                        if block_result:
                            block = enrich_block_reward(block)

                            return self.send_json(
                                {
                                    "type":
                                    "block-hash",
                                    "query":
                                    query,
                                    "data":
                                    block
                                }
                            )

                    except Exception:
                        pass


                    try:
                        tx = get_transactions(
                            query
                        )

                        txs = tx.get(
                            "txs",
                            []
                        )

                        if txs:
                            return self.send_json(
                                {
                                    "type":
                                    "transaction",
                                    "query":
                                    query,
                                    "data":
                                    tx
                                }
                            )

                    except Exception:
                        pass


                return self.send_json(
                    {
                        "error":
                        "No matching block or transaction found",
                        "query":
                        query
                    },
                    404
                )


            self.send_error(404)

        except Exception as error:

            self.send_json(
                {
                    "error":
                    str(error)
                },
                500
            )


    def log_message(
        self,
        format,
        *args
    ):
        pass


if __name__ == "__main__":

    print(
        f"Feelcoin Explorer running on "
        f"http://{HOST}:{PORT}"
    )

    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler
    )

    server.serve_forever()
