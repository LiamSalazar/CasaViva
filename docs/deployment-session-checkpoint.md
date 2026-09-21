# Deployment session checkpoint

This handoff record contains no credentials or secret values.

## Phase A — local verification — 2026-09-21

**PASS**

- `./scripts/verify.sh` completed once after the final harness fix with
  `CASAVIVA_VERIFY_EXIT=0`. Evidence: backend coverage `188 passed, 5 skipped`
  (86.44%), PostgreSQL tests `191 passed, 2 skipped`, and Playwright `38
  passed (10.9m)` with no `error-context.md`.
- The public/contact Turnstile flow is verified end-to-end: a valid test token
  sends a public inquiry, receives 201 and renders confirmation; an invalid
  token receives 400 and renders rejection. Tokens and required consent remain
  enforced by the backend.
- The E2E harness starts from isolated `casaviva_test` PostgreSQL. Its E2E-only
  throttle settings prevent parallel auth and inquiry fixtures from leaking
  rate-limit state; production settings are unchanged.
- Admin/content and analytics assertions use semantic readiness markers; the
  harness prewarms the relevant routes while retaining `next dev --webpack` so
  pages use the live isolated database. The property test waits for the
  functional URL/list result rather than an internal RSC request.
- Local production rehearsal completed with
  `CASAVIVA_REHEARSAL_EXIT=0` and `PASS LOCAL PRODUCTION REHEARSAL`, including
  PostgreSQL persistence,
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
