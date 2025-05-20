# MCP Interaction Rule for Pixel Detective

**Repository:** [Pixel_Detective](https://github.com/rm2thaddeus/Pixel_Detective.git)
**Branches:**
- main
- development

## Best Practices for MCP (AI Assistant) Interactions

1. **Branch Awareness**
   - Always determine the current active git branch before committing or pushing changes (e.g., via `git branch --show-current`).
   - Default to the active branch unless the user specifies otherwise.
   - Main branches for this repository: `main`, `development`.

2. **Commit Messages**
   - Use clear, descriptive commit messages following Conventional Commits style (e.g., `feat:`, `fix:`, `docs:`, `refactor:`).
   - Summarize the intent and scope of the change.

3. **Batching Changes**
   - Prefer batching related changes into a single commit when possible (e.g., code + docs for a new feature).
   - Avoid committing commented-out code or experimental scripts to the main repository.

4. **Documentation**
   - Document any MCP-driven architectural or workflow changes in `/docs/CHANGELOG.md`.
   - For major features or refactors, update or create relevant documentation in `/docs/` (e.g., `architecture.md`, `roadmap.md`).

5. **Safety and Review**
   - Never force-push to shared branches unless explicitly instructed.
   - If a change is potentially breaking or experimental, create a new branch and open a pull request for review.

6. **Transparency**
   - Clearly state when a change is made by MCP in the commit message or PR description.

---

_This rule ensures safe, transparent, and well-documented collaboration between human developers and the MCP AI assistant in the Pixel Detective project._ 