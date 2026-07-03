# HOCH Agent Swarm — Remote Relay Deployment

This directory contains configuration templates for running the Prompt Brain factory on private virtual servers (VPS) or isolated cloud environments.

## Services Setup
1. **Host Setup**: Ensure Docker and docker-compose are installed on the host.
2. **Environment**: Copy `.env.example` to `.env` and fill out tokens.
3. **Caddy Proxy**: Update the domain configurations in `Caddyfile`.
4. **Deploy**: Execute `./scripts/deploy_remote.sh`.
