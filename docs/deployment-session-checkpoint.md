# Deployment session checkpoint

This handoff record contains no credentials or secret values.

## Phase A — local verification — 2026-09-20

**PASS**

- `./scripts/verify.sh` completed with `CASAVIVA_VERIFY_EXIT=0`. Evidence:
  backend coverage `188 passed, 5 skipped` (86.44%), PostgreSQL tests `191
  passed, 2 skipped`, and Playwright `38 passed (11.0m)` with no
  `error-context.md`.
- The public/contact Turnstile flow is verified end-to-end: a valid test token
  sends a public inquiry, receives 201 and renders confirmation; an invalid
  token receives 400 and renders rejection. Tokens and required consent remain
  enforced by the backend.
- The E2E harness starts from isolated `casaviva_test` PostgreSQL. Its E2E-only
  throttle settings prevent parallel auth and inquiry fixtures from leaking
  rate-limit state; production settings are unchanged.
- Navigation assertions wait for a successful RSC response before confirming
  URL/content. Traces showed navigation and 200 RSC responses; Next dev Fast
  Refresh could defer the visible URL commit.
- Local production rehearsal evidence passed: PostgreSQL persistence,
  isolated backup checksum/restore, ops-bundle checksum/version tracking, and
  candidate-failure/manual deployment rollback.
- `terraform fmt -check -recursive infra`, bootstrap and Pilot `terraform
  validate`, `tflint`, and Checkov passed. Checkov: 112 passed, 0 failed, 4
  documented skips.

## Remaining gates before any apply

1. Commit and push the intentional Phase A changes, then require every GitHub
   CI check for that exact SHA to succeed.
2. Use only `AWS_PROFILE=casaviva-deploy` for non-destructive AWS preflight:
   identity, `mx-central-1`, Route53 domain/hosted zone, existing CasaViva
   resources, and Terraform backend.
3. Produce and inspect bootstrap/Pilot plans before any apply. The Pilot plan
   must contain no NAT Gateway, RDS, ALB, ECS, or Growth resources and must be
   reviewed against the Pilot cost target (approximately USD 21–31/month before
   taxes and regional variation).

No AWS resource, DNS record, Terraform apply, or deployment was performed in
this Phase A session.
