# Remote VPS Deployment Runbook

Follow these steps to deploy and run the Prompt Brain and Agent Swarm stack:

## Step 1: Provision Host
* Provision a 4 vCPU, 8GB RAM Ubuntu droplet/VPS with ssh access.

## Step 2: Install Docker Engine
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
```

## Step 3: Synchronize Codebase
* Upload codebase to `/app`.

## Step 4: Configure environment
```bash
cp /app/deploy/remote-relay/.env.example /app/deploy/remote-relay/.env
```
* Fill out `RELAY_AUTH_TOKEN` and `CLOUDFLARE_TUNNEL_TOKEN` inside `.env`.

## Step 5: Start Stack
```bash
cd /app/deploy/remote-relay
docker-compose up -d
```

## Step 6: Verify connection
```bash
./scripts/verify_remote.sh
```

## Step 7: Rollback / Stop
```bash
docker-compose down
```
