# Billing API rollback runbook

1. Pause external payment retries.
2. Revert deployment to previous stable tag.
3. Verify ledger reconciliation and queue drain.
