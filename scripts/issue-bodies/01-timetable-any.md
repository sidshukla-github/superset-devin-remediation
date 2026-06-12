## Problem
The TimeTable visualization utilities use `any` types, which conflicts with Superset TypeScript modernization standards.

## Scope
- Files:
  - `superset-frontend/src/visualizations/TimeTable/utils/sortUtils/sortUtils.ts`
  - `superset-frontend/src/visualizations/TimeTable/types.ts`

## Acceptance criteria
- [ ] Replace `any` with proper types in scoped files
- [ ] `npm run test -- sortUtils.test.ts` passes in `superset-frontend/`
- [ ] `pre-commit run` passes on changed files
- [ ] PR references this issue
