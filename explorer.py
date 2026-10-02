#!/usr/bin/env python3

import json
import re
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

RPC = "http://127.0.0.1:35781"
HOST = "0.0.0.0"
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


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#070b14">

<title>Feelcoin Block Explorer</title>

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
    radial-gradient(circle at 20% -10%,rgba(124,92,255,.18),transparent 36%),
    radial-gradient(circle at 90% 0%,rgba(34,211,166,.08),transparent 30%),
    var(--bg);
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
  position:sticky;
  top:12px;
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
  grid-template-columns:repeat(4,1fr);
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
    display:none;
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
</style>
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
<a href="http://162.35.27.43:4243">Mining Pool</a>
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


function age(ts){
  const diff = Math.max(
    0,
    Date.now() / 1000 - Number(ts || 0)
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

  $("resultDetails").innerHTML = `
    <div class="result-grid">

      ${resultBox("Height",header.height)}
      ${resultBox("Hash",header.hash)}
      ${resultBox("Previous Hash",header.prev_hash)}
      ${resultBox("Timestamp",header.timestamp)}
      ${resultBox("Age",age(header.timestamp))}
      ${resultBox("Difficulty",number(header.difficulty))}
      ${resultBox("Reward",feel(header.reward))}
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


            if parsed.path == "/api/home":

                info = get_info()

                height = int(
                    info.get("height", 0)
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
                        "blocks": blocks
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
