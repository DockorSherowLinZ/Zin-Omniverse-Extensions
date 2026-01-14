# Zin-Omniverse-Extensions

A monorepo template for maintaining multiple NVIDIA Omniverse Kit Extensions long-term.

## Included (example extensions)
- `tw.zin.smart_reference`
- `tw.zin.smart_measure`
- `tw.zin.smart_assets_builder`
- `tw.zin.smart_align`
- Shared core library: `tw.zin.smart_core`

## Quick install (local dev)
1. Clone this repo somewhere on your machine.
2. In Kit / Isaac Sim:
   - **Window → Extensions → Settings (gear) → Extension Search Paths**
   - Add: `<repo_root>/exts`
   - (Optional) Add: `<repo_root>/shared` if you want to load the shared core as an extension too (not required for imports).
3. Enable the extensions by searching `tw.zin.` in Extension Manager.

> Tip: For pure python sharing, the extensions already import from `shared/` via a small sys.path helper.
> If you prefer, you can also convert `shared/` into a proper Kit extension dependency.

## Repo layout
- `exts/` : each extension (Kit discovers these)
- `shared/` : shared python modules (core utils)
- `docs/` : documentation
- `.github/workflows/` : basic CI + release zip packaging

## Development notes
- Each extension is intentionally minimal. Replace the placeholder UI/logic with your real implementation.
- Keep IDs stable: `tw.zin.smart_*` so users don’t lose settings between updates.

## License
MIT (see `LICENSE`)
