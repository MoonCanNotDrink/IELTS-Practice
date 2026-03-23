# Stacked PR Playbook

This file keeps a searchable merge and cleanup checklist for stacked pull requests.

## Current Stack (2026-03-21)

### Free Practice Feature Stack

1. Merge `#3` into `feature/free-practice-speaking`
2. Retarget `#4` from `pr/free-practice-backend` to `feature/free-practice-speaking`
3. Merge `#4`

### Documentation Stack

1. Merge `#5` into `feature/free-practice-speaking`
2. Retarget `#6` from `pr/docs-core` to `feature/free-practice-speaking`
3. Merge `#6`

## Remote Branch Cleanup

Delete branches only after the dependent PR no longer needs them as a base.

- After `#3` is merged and `#4` has been retargeted, delete `pr/free-practice-backend`
- After `#4` is merged, delete `pr/free-practice-ui`
- After `#5` is merged and `#6` has been retargeted, delete `pr/docs-core`
- After `#6` is merged, delete `pr/docs-external`

## Example Commands

```bash
git push origin --delete pr/free-practice-backend
git push origin --delete pr/free-practice-ui
git push origin --delete pr/docs-core
git push origin --delete pr/docs-external

git branch -d pr/free-practice-backend
git branch -d pr/free-practice-ui
git branch -d pr/docs-core
git branch -d pr/docs-external
```

## Search Hints

Search for `stacked`, `merge order`, `retarget`, or `cleanup` to find this file quickly.
