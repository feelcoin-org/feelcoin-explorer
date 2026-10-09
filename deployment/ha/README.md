# Feelcoin Explorer — RPC Failover Infrastructure

## Architecture

Feelcoin Explorer -> local RPC failover proxy

- Primary RPC: 127.0.0.1:35781
- Backup RPC: 127.0.0.1:35795 (SSH tunnel to Node 2)
- Failover proxy: 127.0.0.1:35790

## Design

- Primary-first health verification
- Automatic backup selection when the primary is unhealthy
- Trusted block-height persistence
- Network checkpoint verification
- Restricted RPC method access
- Local-only RPC endpoints
- Automatic SSH tunnel reconnection through systemd

## Deployment

1. Set up and synchronize two independent Feelcoin nodes.
2. Create a dedicated SSH key for forwarding.
3. Restrict the key on Node 2 to the intended RPC destination.
4. Set BACKUP_NODE_HOSTNAME in the tunnel service template.
5. Configure and verify SSH host-key trust.
6. Install and enable the tunnel service on Node 1.
7. Install proxy.py and the failover proxy service on Node 1.
8. Point the Explorer at http://127.0.0.1:35790.
9. Validate primary routing and controlled backup failover.

The bundled proxy contains a Feelcoin-specific checkpoint.
Verify it against the intended network before deployment.

## Security

Never publish SSH private keys, wallet files, credentials,
trusted SSH host files or private server configuration.

The proxy should remain bound to localhost.

## Limitations

This provides RPC-level failover for the Explorer only.
It does not protect against a complete Node 1 VPS outage.

A backup is rejected when it falls too far behind the last
trusted primary height, but that check alone cannot prove
fresh network consensus during a long primary outage.

These service files are deployment templates, not an
automated installation script.

## Environment-specific configuration

These examples reflect the original Feelcoin deployment.

Before using them on a new server:

- Replace the `feeladmin` service account and home directory if needed.
- Adjust the Explorer installation path.
- Replace `BACKUP_NODE_HOSTNAME` with the intended backup host.
- Verify the SSH forwarding key and host-key configuration.
- Confirm the RPC ports and Feelcoin checkpoint.
- Ensure `/var/lib/feelcoin-rpc-failover/` is writable by the proxy service.

The provided files are templates. They do not automatically
configure or secure the backup node's SSH server.
