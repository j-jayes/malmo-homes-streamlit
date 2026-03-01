# 2026-03-01 Active Workflow Hotfix Checklist

## Scope
Stabilize the active listings GitHub Actions workflow after first manual validation run.

## Tasks
- [x] Identify exact failure cause from workflow logs.
- [x] Prevent missing manifest helper from failing the run.
- [x] Fix artifact upload path to avoid absolute-path root expansion.
- [x] Ensure workflow token has permission to create issues on failure.
- [ ] Re-run low-volume manual active workflow validation.
- [ ] Confirm Azure OIDC login and blob upload complete successfully.
