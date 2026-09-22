# Local Project Cleanup

The Git repository itself is not carrying the 36k+ generated files: the current V4 release tree contains 269 tracked entries, and no tracked `node_modules`, `.next`, Python cache, Playwright artifact, or runtime-generated directories were found.

The large local count is therefore expected to come from generated development artifacts such as dependency folders, Next.js build output, Python caches, and Playwright test output.

## Safe cleanup

From the repository root on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cleanup-local-project.ps1
```

That command is preview-only.

To actually delete the generated dependency/build/test caches:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cleanup-local-project.ps1 -Apply
```

The script intentionally leaves `backend/runtime_*` and root `runtime_*` directories alone because those can contain local development state.

After cleanup, reinstall only what is needed:

```powershell
cd frontend
npm install

cd ..\e2e
npm install
```

Run the browser tests only when needed; Playwright will recreate its output directories.

## Release-safety note

This cleanup branch is separate from the frozen V4 release candidate. Do not merge it into `v4/saas-foundation` while exact-SHA release observation is in progress; merging anything into that branch creates a new release candidate and invalidates prior exact-SHA observation evidence.
