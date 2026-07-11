# Agentic Commerce Stack — Demo Agent

Agente de referencia que demuestra el loop completo de comercio agente-a-agente (M2M)
sobre el stack LATAM de teodorofodocrispin-cmyk:

- 🛡️ TrustBoost — PII sanitization (https://api.trustboost.dev)
- 🧠 Intelica — Competitive intelligence (https://api.intelica.dev)
- ✅ VeraData — Verified LATAM data / sanctions (https://api.veradata.dev)

El agente:
1. Descubre dinámicamente los 3 servicios leyendo su `agent-card.json` + `/pricing` (Fase A).
2. Paga cada llamada vía x402 (USDC en Base mainnet) — sin cuentas, sin API keys.
3. Encadena: TrustBoost /sanitize → Intelica /intel → VeraData /sanctions.
4. Devuelve un reporte unificado con los 3 tx hashes.

Esto es un cliente EXTERNO: no tiene acceso a los cores privados de ningún servicio.
Solo llama los endpoints públicos como cualquier agente autónomo lo haría.

## Uso
```bash
export AGENT_WALLET_KEY_FILE=~/.agent_wallet.key
python run_agent.py --target "Empresa Ficticia S.A.S. Colombia"
```
