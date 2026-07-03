# Remote Runtime Deployment Guide

This guide describes VPS installation processes:

## Prerequisites
* Linux server with Docker Engine 20.10+ and docker-compose installed.
* Cloudflare Account with Tunnel configured.

## Configuration Steps
1. Clone repository to `/app`.
2. Configure `.env` file from template.
3. Start stack with `deploy_remote.sh`.
4. Validate boundary check endpoints are returning HTTP 200.
