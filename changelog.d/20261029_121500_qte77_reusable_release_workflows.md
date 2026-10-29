### Changed

- Release workflows (`bump-my-version.yaml`, `tag-release.yaml`, `publish-release.yaml`) are now thin callers of the shared `qte77/.github` reusable workflows. The bump commit is now created and signed through the GitHub API; uv.lock sync, scriv collect, tag-on-main and the never-delete/never-overwrite guards are unchanged.
