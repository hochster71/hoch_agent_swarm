#!/bin/bash
# Start the ngrok tunnel for Stripe webhook development.
#
# Static domain: portfolio-hoch-agent-swarm.ngrok-free.dev
# Webhook URL:   https://portfolio-hoch-agent-swarm.ngrok-free.dev/api/stripe/webhook
#
# Register the webhook URL in Stripe Dashboard -> Developers -> Webhooks -> Add endpoint.
# Subscribe to: checkout.session.completed, invoice.paid, invoice.payment_failed,
#               customer.subscription.updated, customer.subscription.deleted
#
# Copy the resulting whsec_... signing secret into .env as STRIPE_WEBHOOK_SECRET.
#
# Run this script whenever you need Stripe to reach your local backend.
# The tunnel stays open as long as this process runs.
# Ref: https://ngrok.com/blog/free-static-domains-ngrok-users
set -euo pipefail
DOMAIN="portfolio-hoch-agent-swarm.ngrok-free.dev"
PORT="${HAS_PORT:-8000}"
echo "Starting ngrok tunnel -> localhost:$PORT"
echo "Stripe webhook URL: https://$DOMAIN/api/stripe/webhook"
echo "Inspect traffic at: http://127.0.0.1:4040"
ngrok http "$PORT" --domain="$DOMAIN" --log=stdout
