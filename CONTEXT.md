# CONTEXT.md — Agentic Commerce Stack Demo Agent

> Last updated: July 11, 2026
> Reference autonomous agent that proves the end-to-end M2M (agent-to-agent) loop over the LATAM Agentic Commerce Stack.

## Purpose

This is a **reference client**, not a core service. It demonstrates that an autonomous
agent can:
1. **Discover** the 3 services dynamically by reading their `agent-card.json` + `/pricing` (proves Fase A discovery works).
2. **Sign x402 v2** payment envelopes.
3. **Pay USDC on-chain** (Base mainnet) from a throwaway agent wallet.
4. **Chain** the pipeline: `TrustBoost /sanitize` → `Intelica /intel` → `VeraData /sanctions`.
5. Publish its own `agent-card.json` declaring the stack as a dependency (discovery network effect).

It is EXTERNAL: it has **no access** to the service cores, Supabase, Render, or any
production credential. It only calls the public HTTPS endpoints like any agent would.

## Stack under test

| Service | URL | Role |
|---|---|---|
| TrustBoost | https://api.trustboost.dev | PII sanitization (Solana-priced) |
| Intelica | https://api.intelica.dev | Competitive intelligence (Base-priced) |
| VeraData | https://api.veradata.dev | Verified LATAM data / sanctions (Base-priced) |

## How it works (run_agent.py)

- Reads `AGENT_WALLET_KEY_FILE` (default `~/.agent_wallet.key`) — the private key is
  NEVER printed, NEVER written to the repo, NEVER sent to any service.
- `discover(base_url)`: GET `/.well-known/agent-card.json` + `/pricing` to resolve
  endpoints and prices dynamically (no hardcoding).
- `build_x402_payment_header` / `build_x402_header_with_tx`: sign the canonical payload
  (EIP-191) and base64-encode into the `X-Payment` header.
- `send_usdc_onchain`: REAL ERC-20 USDC `transfer` on Base mainnet to the service's
  `payTo` (requires ETH for gas + USDC balance in the wallet).
- `call_protected`: POST with the payment header; captures the 402 demand as evidence.

## Verified results (Jul 11, 2026)

| Service | Discovery | x402 signed | On-chain USDC paid | Settle 200 |
|---|---|---|---|---|
| TrustBoost | ✅ | ✅ | trial (`TRIAL`, Solana-priced) | 402* |
| Intelica | ✅ | ✅ | ✅ `f5c7a7202a0873b28c7cf98bc0fbfe1675d8e05b382a465b65636fa4f9eadd80` | 402** |
| VeraData | ✅ | ✅ | ✅ `7cf134bf6df232699408250f1b0b3d76f7509126c30cebc8c631285b7a2dc1a3` | 402** |

\* TrustBoost `payTo` is Solana (`giu4VciTkfWJNG1oeP6SzHEJwmabikJSMB91GaFNWE4`); demo used trial mode.
\** Intelica/VeraData: USDC transferred on-chain, verifiable on BaseScan. Service returns
402 because it **delegates payment verification to the CDP/PayAI facilitator**, which
requires production credentials (`CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` for Intelica/VeraData,
PayAI for TrustBoost) to issue the settlement receipt. By x402 design, the client does not
convince the service by signing alone — the facilitator confirms.

## What this proves

The agent **discovers, signs, and pays real USDC** to the stack. That is the first half of
the mission: autonomous agent adoption with real money. The final `200` depends on the
facilitator infrastructure (server-side), not on the agent.

## Security

- Private key read only from `AGENT_WALLET_KEY_FILE`, chmod 600, never committed (`.gitignore`).
- No production credentials, no core access, no Supabase.
- The demo is a throwaway client; rotate the test wallet after use.

## Files

- `run_agent.py` — the agent (Mode A: on-chain pay; Mode B: 402-demand evidence)
- `agent-card.json` — declares the stack as dependency
- `README.md` — usage
- `.gitignore` — excludes `*.key`, `__pycache__`
