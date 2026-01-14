# Smart Core (`tw.zin.smart_core`)
Shared utilities for Zin's Omniverse extensions.

This is not a Kit extension by default. It's a shared python module folder.
Extensions add this folder to `sys.path` automatically via a tiny helper.

If you prefer dependency-based loading, you can convert this into a proper Kit extension
later (add extension.toml + python.module).
