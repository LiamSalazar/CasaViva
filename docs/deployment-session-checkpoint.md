# Deployment session checkpoint

This file is an operational handoff record.  It contains no credentials or other
secret values.

## A — Local completion

- Commit under review: `a84e1e0`.
- Status: **IN PROGRESS**.
- Completed evidence: the repository worktree was clean before this session;
  targeted backend, ops-bundle, and rollback rehearsals completed successfully
  in the preceding local readiness pass.  A new sequential `verify.sh` run was
  started to make the final Phase A result reproducible.
- Local correction made this session: manual deployment now proves that the
  selected SHA is an ancestor of `origin/main`, in addition to requiring a
  successful CI run for that exact SHA.
- AWS resources created: none.
- Production public: no.
- Demo running: no.
- Next command: `./scripts/verify.sh` (complete the sequential run), followed
  by `./scripts/rehearse-production.sh` and Terraform validation/scanners.

## Preconditions before AWS phases

- The deployment operator must configure the local `casaviva-deploy` AWS
  profile without placing bootstrap credentials in this repository or command
  history.
- A real owned production domain, a real demo subdomain, and the legal
  responsible address are required before public production DNS/readiness.
- Founder identities and an MFA enrollment are an explicit human checkpoint.
