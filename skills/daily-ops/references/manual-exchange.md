# Manual exchange when the runtime is unavailable

Use this workflow in a chat environment without Python or persistent folder access. A skill or plugin installation is different from attaching a document to a chat. Do not claim the runtime is installed just because this guide was uploaded.

1. Ask the user to provide the current Daily Ops export, or a small list of tasks they choose to share. Never claim access to a local folder or connected account that the host has not exposed.
2. Ask for the date and available task minutes. Suggest a small plan, explicitly showing the arithmetic and what does not fit. Label it a proposed plan.
3. If the user supplied a JSON export, prepare a change proposal using its exact revision and stable task IDs. Follow [changes.md](changes.md). If they supplied only free text, give a plain-language proposal rather than inventing a revision or pretending to update state.
4. The user or an execution-capable assistant saves the proposal and runs the local `preview` and `apply` commands. Until that happens, say the workspace has not changed.

For a ChatGPT Project, the public `docs/chat-project.md` can be used as project instructions. Only upload personal task data you want that provider to process. Re-export after changes rather than treating an old conversation as the current task store.
