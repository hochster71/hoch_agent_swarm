# HASF Invoice and Payment Flow

1. **Intake**: Client inputs metadata and selects a subscription tier.
2. **Billing Generation**: API triggers a Stripe Billing session in test-mode.
3. **Fulfillment**: Webhook receives confirmation and enables client scans.
