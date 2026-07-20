# HELM Command Alexa Custom Skill

This directory contains the Alexa Custom Skill package configuration, interaction models, Lambda handler, and OAuth 2.0 Account Linking specification.

## Deployment Instructions

1. Install the Alexa Skills Kit (ASK) CLI:
   ```bash
   npm install -g ask-cli
   ```
2. Configure AWS and ASK credentials:
   ```bash
   ask configure
   ```
3. Deploy the skill package and Lambda function:
   ```bash
   ask deploy
   ```
4. Configure Account Linking in the Alexa Developer Console using the OAuth settings documented in `account-linking/configuration.example.json`.
