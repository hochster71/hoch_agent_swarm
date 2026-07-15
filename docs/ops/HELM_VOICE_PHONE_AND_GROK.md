# HELM Voice — Phone (Tailscale) + Grok + ElevenLabs

**Origin (Tailnet HTTPS):** `https://michaels-macbook-pro.tail826763.ts.net`  
**Proxied to:** `http://127.0.0.1:8770` (HELM LIVE + Voice)  
**Local:** `http://127.0.0.1:8770/voice`

---

## Phone (iPhone on Tailscale)

1. iPhone on same Tailnet (Tailscale app signed in as Michael).
2. Safari → **https://michaels-macbook-pro.tail826763.ts.net/voice**
3. Enable speech · TTS **Auto** or **ElevenLabs** (when READY).
4. Tap **Brief** / **Revenue** / **Sec HIGH**.

Founder cockpit: `.../founder` · Console: `.../console`

If page fails: Mac must be awake, HELM on 8770, Tailscale serve active  
(`tailscale serve status` should show `/ → 127.0.0.1:8770`).

---

## Keep-alive (launchd)

```bash
# Install / reinstall
cp deploy/launchd/com.hoch.helm.voice.plist ~/Library/LaunchAgents/
launchctl bootout "gui/$(id -u)/com.hoch.helm.voice" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.hoch.helm.voice.plist
launchctl kickstart -k "gui/$(id -u)/com.hoch.helm.voice"

# Status
launchctl print "gui/$(id -u)/com.hoch.helm.voice" | head -40
bash scripts/verify_helm_voice.sh
```

Manual start (dev):

```bash
bash scripts/start_helm_voice.sh
```

Secrets: gitignored `.env` / `.env.elevenlabs` only.

---

## Grok Voice Agents binding

1. Persona: paste from `docs/prompts/helm_voice_executive_commander.md`
2. Tool pack (Tailnet origin):

```bash
export HELM=https://michaels-macbook-pro.tail826763.ts.net
curl -sk "$HELM/api/v1/helm/voice/grok-pack?base_url=$HELM&format=md" -o /tmp/helm-grok-pack.md
```

Or open: `docs/prompts/GROK_VOICE_TOOL_PACK_LIVE.md` (regenerated with live origin).

3. **Network honesty:** Tailscale HTTPS is **tailnet-only**.  
   - **Works:** iPhone Safari → tailnet `/voice` (phone on Tailscale).  
   - **Works:** Mac browser → local or tailnet.  
   - **Usually does NOT work:** Grok cloud servers calling your Tailscale origin (they are not on your tailnet).  
   - **Options for Grok tools:** (a) use Grok Voice as conversation + open HELM desk on phone for truth,  
     (b) run tool bridges only from a machine on the tailnet,  
     (c) founder-only: enable **Tailscale Funnel** (public HTTPS) — security tradeoff, not enabled by default.

4. TTS for Grok:
   - Prefer Grok built-in voices if available.
   - Else `POST .../api/v1/helm/voice/tts/speak` with `format=json` (ElevenLabs via HELM).

---

## Smoke

```bash
bash scripts/verify_helm_voice.sh
curl -sk https://michaels-macbook-pro.tail826763.ts.net/api/v1/helm/voice/tts/status | python3 -m json.tool
```
