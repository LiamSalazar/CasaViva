# Deployment session checkpoint

This file is an operational handoff record.  It contains no credentials or other
secret values.

## Final pre-apply review — 2026-09-17

**NOT READY FOR TERRAFORM APPLY**

Only the following blockers remain:

1. The local filesystem has 184 MiB free (100% used).  A fresh `verify.sh`
   run reached backend unit tests (188 passed, 5 skipped, coverage 86.44%) and
   PostgreSQL tests, then Docker Buildx failed while building the frontend with
   `no space left on device`.  The remaining Docker frontend, lint, typecheck,
   production build, audit/scans, ops/rollback and Playwright evidence must be
   rerun after an operator frees local disk space.
2. The required local AWS profile `casaviva-deploy` is absent.  Therefore AWS
   identity/domain/hosted-zone/resource preflight, backend existence check and
   the real Terraform plan cannot be performed.  No credentials were read,
   copied or written.
3. `tflint`, `checkov` and `gh` are not installed/authenticated in this
   workstation, so their final runs and exact-SHA remote CI/environment review
   remain pending.

Completed in this session: clean starting tree inspected; Terraform fmt and
bootstrap/Pilot validate passed; OIDC deployment trust now accepts only
`repo:LiamSalazar/CasaViva:environment:production`; operational documentation
now uses `casaviva-hogar.com`.  No AWS resources, DNS records, Terraform apply
or deployment were performed.

## Preconditions before AWS phases

- The deployment operator must configure the local `casaviva-deploy` AWS
  profile without placing bootstrap credentials in this repository or command
  history.
- A real owned production domain, a real demo subdomain, and the legal
  responsible address are required before public production DNS/readiness.
- Founder identities and an MFA enrollment are an explicit human checkpoint.
