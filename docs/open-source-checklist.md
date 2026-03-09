# Open Source Release Checklist

## A. Functionality

- [ ] `python3 scripts/first_run_onboarding.py --no-input` runs without syntax/runtime errors
- [ ] `python3 scripts/manage_services.py start` works on clean environment
- [ ] Telegram startup message and YES/NO flow verified
- [ ] `MODE=dry-run` behavior confirmed

## B. Security (must pass)

- [ ] `.env` is not tracked by git
- [ ] runtime files and logs are ignored by `.gitignore`
- [ ] `references/env.example` has no real secret values
- [ ] `python3 scripts/security_preflight.py` returns pass
- [ ] No token/private key in docs, scripts, tests, sample outputs

## C. Documentation

- [ ] `docs/quickstart-onboarding.md` up-to-date
- [ ] `docs/help-center.md` links and commands valid
- [ ] `docs/runbook.md` covers start/stop/restart + common failures
- [ ] `SECURITY.md` included and accurate

## D. Release command suggestion

From workspace root:

```bash
git status
git diff --stat
python3 skills/openclaw-hyperliquid-copytrade/scripts/security_preflight.py
```

Only publish when all checks are green.

## E. Optional hard guard (recommended)

Install a git pre-commit hook to auto-run secret scan:

```bash
bash skills/openclaw-hyperliquid-copytrade/scripts/install_git_hook.sh
```

Verify hook:

```bash
git config --get core.hooksPath
```

Expected output: `.githooks`
