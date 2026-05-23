# SafeClaw Roadmap TODO

## Tomorrow: Make Mac Chat Feel Fluid

The Mac app chat should feel like a real assistant workspace, not a terminal log
inside a window. The next pass should focus on speed, clarity, approvals, and
smoother file/link workflows.

### Highest Impact

- [x] Streaming responses with partial output, stop, retry, failed, and done states.
- [x] Approval cards inside chat for file writes, patches, shell commands, network fetches, and WhatsApp sends when the CLI emits an approval prompt.
- [x] Clean result rendering so assistant text, command output, diffs, errors, and file references are visually separate.
- [x] Attachment preview drawer for dropped files and links.

### Chat Workflow

- [x] Recent sessions list with timestamps.
- [x] Rename, delete, export, and quick-switch sessions.
- [x] Starter action chips:
  - Run doctor
  - Explain config
  - Check WhatsApp setup
  - Summarize folder
  - Inspect dropped file
- [x] Message lifecycle states:
  - queued
  - running
  - needs approval
  - stopped
  - failed
  - done

### Attachment UX

- [x] Whole chat drop overlay with "Drop to attach".
- [x] File/link count before send.
- [x] Show file name, size, type, and path.
- [x] Warn when dropped files are outside the configured workspace.
- [x] Let users choose "send as reference" or "include contents".
- [x] Warn before including huge files.

### Context and Safety

- [x] Show active workspace above the composer.
- [x] Show active model above the composer.
- [x] Show active permission profile above the composer.
- [x] Show approval mode above the composer.
- [x] Add allow once, deny, and always allow for this session buttons for approval cards.

### Memory Controls

- [x] Remember this.
- [x] Forget last message.
- [x] Search memory.
- [x] Export session.

### Remaining Follow-Up

- [ ] Replace approval prompt detection with a structured JSON approval protocol from the CLI.
- [ ] Add true token streaming from the model layer instead of only streaming process stdout chunks.
- [ ] Add richer diff/file renderers once the CLI emits structured result events.

## Next: OpenClaw-Style Power and Fluidity

SafeClaw should not try to become the biggest agent platform. It should become
the local agent that feels powerful, fast, and safe enough to trust. These are
the missing pieces to close the gap.

### Provider Polish

- [x] Add provider presets for OpenAI, Ollama, Groq, OpenRouter, LiteLLM, and custom OpenAI-compatible endpoints.
- [x] Add `safeclaw provider-presets`.
- [x] Add `safeclaw provider-test`.
- [ ] Add native Anthropic/Claude adapter.
- [ ] Add native Ollama model discovery.
- [ ] Detect model capabilities: tool calling, streaming, vision, context size.
- [ ] Add fallback model configuration for outages, quota errors, and slow providers.
- [ ] Improve provider error recovery with fix buttons in the Mac app.

### Agent Planning

- [ ] Add plan-before-action mode.
- [ ] Show task steps before running tools.
- [ ] Let users approve or edit the plan before execution.
- [ ] Execute plan steps one by one with visible progress.
- [ ] Retry failed steps with clear explanation.
- [ ] Summarize what changed at the end of every task.

### Tool Depth

- [x] Add `read_many_files`.
- [x] Add `create_file`.
- [x] Add `move_file`.
- [x] Add `delete_file` with approval and backup behavior.
- [x] Add `diff_file`.
- [x] Add `git_status`.
- [x] Add `git_diff`.
- [ ] Add `git_commit` with approval.
- [x] Add `run_tests`.
- [ ] Add `install_package` with approval.
- [ ] Add document/PDF parsing.
- [ ] Add browser/search tools only after permissions are strong enough.
- [ ] Add image/file attachment understanding.

### Approval UX

- [x] Render approval cards with exact file path, command, URL, or WhatsApp recipient.
- [ ] Show before/after file diffs before writes and patches.
- [ ] Support allow once, deny, and always allow for this session through structured CLI events.
- [ ] Add "why does SafeClaw need this?" explanations.
- [ ] Add an approval/audit trail per session.
- [ ] Add a panic switch to disable shell, network, and messaging actions.

### Memory and Workspace Awareness

- [ ] Add memory search UI.
- [ ] Add edit/delete memory UI.
- [ ] Add memory scopes: global, workspace, session, contact.
- [ ] Add "remember this?" chips after useful answers.
- [ ] Add a memory privacy view.
- [ ] Always show current workspace, indexed file count, permission profile, model provider, and last tool used.

### Fluid Chat and Artifacts

- [ ] Add stop, retry, regenerate, and continue controls everywhere.
- [x] Add collapsible tool logs.
- [ ] Add artifact cards for plans, file diffs, command results, errors, memories, exports, and timelines.
- [ ] Add conversation search.
- [ ] Make session history feel native and persistent.
- [ ] Keep raw logs in Output, never in the main response unless requested.

### WhatsApp Companion

- [ ] Add a full WhatsApp setup wizard in the Mac app.
- [x] Add Twilio fields directly in the WhatsApp tab.
- [x] Add webhook URL guidance and tunnel setup guidance.
- [ ] Add service status indicator.
- [ ] Add test message button.
- [ ] Add sender allowlist editor.
- [x] Keep the persistent background service easy to install, start, stop, and inspect.
- [ ] Add "message me when task is done" for long-running tasks.

### Jarvis Mode

- [ ] Implement real push-to-talk voice input.
- [ ] Add local Whisper or `whisper.cpp` transcription option.
- [ ] Add transcript preview before sending.
- [ ] Add optional text-to-speech responses.
- [ ] Add background task queue persistence.
- [ ] Add desktop notifications.
- [ ] Add WhatsApp handoff when the user walks away.
- [ ] Add task status dashboard and daily summaries.

### Installer and Onboarding

- [ ] Build a real double-click Mac installer flow.
- [ ] Add provider setup wizard with validation.
- [ ] Add Ollama install and model download flow.
- [ ] Add doctor fix buttons.
- [ ] Add "try sample task" button.
- [ ] Make first run require no terminal for non-dev users.

### Legal Workflow Ideas

- [ ] Add matter mode: `safeclaw matter create`.
- [ ] Add matter intake questionnaire.
- [ ] Add contract review with source-grounded summaries.
- [ ] Add contract comparison/redline assistant.
- [ ] Add litigation timeline builder.
- [ ] Add discovery/evidence index.
- [ ] Add deposition prep outline generator.
- [ ] Add client update drafter.
- [ ] Add billing narrative helper.
- [ ] Add local clause library.
- [ ] Add legal-specific permission profiles such as `legal-readonly`, `legal-workspace-write`, and `legal-no-network`.

### Implementation Notes

- Keep raw CLI logs in the Output tab.
- The Chat tab should render human-readable assistant responses first.
- Dangerous transitions should be visible before they run.
- The biggest unlock is approval cards inside chat, followed by streaming
  responses and session history.
