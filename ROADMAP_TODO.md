# SafeClaw Roadmap TODO

## Tomorrow: Make Mac Chat Feel Fluid

The Mac app chat should feel like a real assistant workspace, not a terminal log
inside a window. The next pass should focus on speed, clarity, approvals, and
smoother file/link workflows.

### Highest Impact

- [ ] Streaming responses with partial output, stop, retry, failed, and done states.
- [ ] Approval cards inside chat for file writes, patches, shell commands, network fetches, and WhatsApp sends.
- [ ] Clean result rendering so assistant text, command output, diffs, errors, and file references are visually separate.
- [ ] Attachment preview drawer for dropped files and links.

### Chat Workflow

- [ ] Recent sessions list with timestamps.
- [ ] Rename, delete, export, and quick-switch sessions.
- [ ] Starter action chips:
  - Run doctor
  - Explain config
  - Check WhatsApp setup
  - Summarize folder
  - Inspect dropped file
- [ ] Message lifecycle states:
  - queued
  - running
  - needs approval
  - stopped
  - failed
  - done

### Attachment UX

- [ ] Whole chat drop overlay with "Drop to attach".
- [ ] File/link count before send.
- [ ] Show file name, size, type, and path.
- [ ] Warn when dropped files are outside the configured workspace.
- [ ] Let users choose "send as reference" or "include contents".
- [ ] Warn before including huge files.

### Context and Safety

- [ ] Show active workspace above the composer.
- [ ] Show active model above the composer.
- [ ] Show active permission profile above the composer.
- [ ] Show approval mode above the composer.
- [ ] Add allow once, deny, and always allow for this session buttons for approval cards.

### Memory Controls

- [ ] Remember this.
- [ ] Forget last message.
- [ ] Search memory.
- [ ] Export session.

### Implementation Notes

- Keep raw CLI logs in the Output tab.
- The Chat tab should render human-readable assistant responses first.
- Dangerous transitions should be visible before they run.
- The biggest unlock is approval cards inside chat, followed by streaming
  responses and session history.
