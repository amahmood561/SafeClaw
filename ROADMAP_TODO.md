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

### Implementation Notes

- Keep raw CLI logs in the Output tab.
- The Chat tab should render human-readable assistant responses first.
- Dangerous transitions should be visible before they run.
- The biggest unlock is approval cards inside chat, followed by streaming
  responses and session history.
