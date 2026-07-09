# K-Track Founder Action Packet

This packet details the manual actions required from Michael to resolve credential and infrastructure blocks (K1-K6).

> [!WARNING]
> Do not share any API keys, passwords, or SSH credentials in the agent chat window. Store all sensitive parameters locally in the designated files.

---

## K-Track Actions & Steps

### K1: OPENAI / ANTHROPIC Provisioning [RESOLVED]
- **Status**: Completed (2026-07-06).
- **Action**: Provide API credentials.
- **Why it matters**: Unblocks Rung 2 live evaluations and active critic seats.
- **Safe Steps**:
  1. Retrieve active keys from OpenAI & Anthropic consoles.
  2. Write them locally into:
     - `.env` (Done via `configure_ai_keys.py`)
- **Risk if deferred**: None (Resolved).

### K2: Apple Developer Access [RESOLVED]
- **Status**: Completed (2026-07-06).
- **Action**: Register Apple Developer Account and invite agent.
- **Why it matters**: Awaiting App Store Connect integration.
- **Safe Steps**:
  1. Go to [developer.apple.com](https://developer.apple.com) and complete registration (Done).
  2. Add the agent email under App Store Connect Users list.
- **Risk if deferred**: None (Resolved).

### K3: App Store Connect & Bundle ID
- **Action**: Create identifier `com.hasf.rmfcompanion`.
- **Why it matters**: Standardizes the product namespace.
- **Safe Steps**:
  1. Register `com.hasf.rmfcompanion` in Apple Developer portal.
  2. Create App entry in App Store Connect.
- **Risk if deferred**: Build profiles will reject packaging due to identifier mismatch.

### K4: Signing Certificates
- **Action**: Generate iOS Distribution Certificates and Provisioning Profiles.
- **Why it matters**: Validates binary integrity for Apple review.
- **Safe Steps**:
  1. Generate CSR from Keychain and upload to Apple portal.
  2. Download Distribution Certificate and Provisioning Profile.
  3. Install in developer Keychain.
- **Risk if deferred**: App cannot be installed on iOS devices.

### K5: Remote Host Credentials
- **Action**: Provision SSH credentials for `HOCH-200`.
- **Why it matters**: Secures connection to the always-on server.
- **Safe Steps**:
  1. Generate SSH key pair.
  2. Install public key on HOCH-200.
  3. Write local config into `.secrets/ssh_config`.
- **Risk if deferred**: Daemon cannot run on bare metal.

### K6: Secrets Inventory
- **Action**: Review and approve repository secrets list.
- **Why it matters**: Prevents credential leaks.
- **Safe Steps**:
  1. Run local scan scripts.
  2. Validate `.gitignore` excludes `.secrets/` and `.env`.
- **Risk if deferred**: Exposure of developer API keys.
