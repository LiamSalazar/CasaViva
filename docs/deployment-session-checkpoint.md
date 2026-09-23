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

## AWS Pilot production handoff — 2026-09-23

**DONE — production operational handoff**

- Final release: `3ae67d4a148cf577242955b7b6cdeaaecfc2700c`. Exact CI passed
  (`35877871210`); Deploy Pilot is manual-only.
- Deploy Pilot fix run `35879627870` succeeded. The real rollback command
  `2ff1666a-93b8-4a56-bf4f-3a533aa658b1` succeeded, authenticated to ECR
  just-in-time through the EC2 IAM role, and explicitly did not reverse
  database migrations. Restore run `35891333292` succeeded.
- Release state is coherent: current application/ops and running backend/
  frontend are `3ae67d4...`; previous application/ops are
  `19dca5698f0656579fb006779f29440ed72ac1fd`.
- Public production is healthy: apex and `www` TLS validate, `www` redirects
  to the apex, `/`, live, ready, Privacy `integral-2026-09`, and Terms
  `terms-2026-09` return 200. HSTS is exactly one header with `max-age=3600`
  and no `includeSubDomains` or `preload`.
- Production readiness passes with zero critical blockers. PostgreSQL remains
  healthy on EBS `vol-0cc53e5e1d2e0e9fc` mounted at `/opt/casaviva/postgres`;
  backup timer and CloudWatch Agent are active. Liam remains present with MFA;
  one Privacy and one Terms version are active.
- Security gates remain satisfied: only 80/443 are public; 22, 5432, 3000,
  8000, and 8443 are not public; S3 buckets are private; IMDSv2 is required;
  runtime AWS access uses the EC2 IAM role; GitHub deployment uses OIDC.
- Pilot Terraform plan against the remote state returned `No changes` with
  detailed exit code 0. No Terraform apply, DNS, certificate, HSTS, or
  infrastructure change was performed during closeout.

The temporary local operator identity `CasaViva_RootDeployment` still has one
active access key and `AdministratorAccess`. It was not removed. Based on the
validated GitHub OIDC deployment, EC2 instance role, and absence of runtime
static credentials, it is safe for the operator to remove that temporary key
after arranging any replacement credentials needed for future local Terraform
operations.
