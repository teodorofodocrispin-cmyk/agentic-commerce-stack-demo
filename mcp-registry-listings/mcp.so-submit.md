# MCP.so Submission Data — Agentic Commerce Stack for LATAM

MCP.so auto-discovers from GitHub, but to ensure VeraData and Intelica are
listed (TrustBoost is already live at mcp.so/server/trustboost-pii-sanitizer/teodorofodocrispin-cmyk),
submit these manually at https://mcp.so/ (or wait for auto-index from the repos below).

## VeraData
- Server name: veradata
- Display: VeraData — Verified LATAM Data (x402)
- MCP URL: https://api.veradata.dev/mcp
- Homepage: https://api.veradata.dev
- Repository: https://github.com/teodorofodocrispin-cmyk/veradata-public
- Description: Verified Latin American data for autonomous AI agents via x402 micropayments.
  Sanctions screening (OFAC+UN+EU+UK, 59k+ entries), entity enrichment (RUES/CNPJ/RFC),
  central bank rates (DTF/TIIE/Selic/TRM/UF), business registry, and AI-powered market context.
  EU AI Act Art.13 compliant audit trails. $0.02–$0.10 USDC per call on Base and Solana.
- Tags: latam, compliance, enrichment, financial-data, x402, sanctions, kyb, kyc
- Payment: x402 (Base eip155:8453 + Solana), AP2-compatible

## Intelica
- Server name: intelica
- Display: Intelica — Competitive Intelligence (x402)
- MCP URL: https://api.intelica.dev/mcp
- Homepage: https://api.intelica.dev
- Repository: https://github.com/teodorofodocrispin-cmyk/Intelica-docs
- Description: Competitive intelligence API for autonomous AI agents. Moat scoring (IMI),
  competitor mapping, executive brief, strategic recommendations against a graph of 3,600+ companies.
  Decision-trust layer: every analysis auditable and traceable. $0.05 USDC/call on Base/Solana via x402.
- Tags: competitive-intelligence, market-analysis, decision-support, x402, agentic-commerce
- Payment: x402 (Base eip155:8453 + Solana), AP2-compatible

## TrustBoost (already listed)
- URL: https://mcp.so/server/trustboost-pii-sanitizer/teodorofodocrispin-cmyk
- Action: verify card shows ap2_compatible + Base network (update if needed via repo)

## How to submit
1. Go to https://mcp.so/ → "Submit a server" (or "Add MCP Server").
2. Paste the MCP URL above (https://api.<service>.dev/mcp).
3. MCP.so fetches the server-card.json automatically (now served at
   /.well-known/mcp/server-card.json for VeraData, and /mcp-server-card.json for Intelica/TrustBoost).
4. Confirm tags + payment metadata.
