import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAC_APP = ROOT / "mac-app"
PACKAGE_JSON = MAC_APP / "package.json"
MAIN_JS = MAC_APP / "src" / "main.js"
PRELOAD_JS = MAC_APP / "src" / "preload.js"
RENDERER_JS = MAC_APP / "src" / "renderer.js"
INDEX_HTML = MAC_APP / "src" / "index.html"
STYLES = MAC_APP / "src" / "styles.css"
APP_README = MAC_APP / "README.md"
CAPTURE_SCRIPT = MAC_APP / "scripts" / "capture-screenshots.js"


def test_electron_mac_app_files_exist():
    for path in [PACKAGE_JSON, MAIN_JS, PRELOAD_JS, RENDERER_JS, INDEX_HTML, STYLES, APP_README, CAPTURE_SCRIPT]:
        assert path.exists(), path


def test_electron_package_has_expected_scripts_and_metadata():
    package = json.loads(PACKAGE_JSON.read_text())

    assert package["name"] == "safeclaw-mac-app"
    assert package["main"] == "src/main.js"
    assert package["scripts"]["start"] == "env -u ELECTRON_RUN_AS_NODE electron ."
    assert "electron" in package["devDependencies"]
    assert package["build"]["appId"] == "com.safeclaw.app"
    assert package["build"]["productName"] == "SafeClaw"


def test_electron_javascript_syntax_is_valid():
    for path in [MAIN_JS, PRELOAD_JS, RENDERER_JS, CAPTURE_SCRIPT]:
        result = subprocess.run(
            ["node", "--check", str(path)],
            cwd=MAC_APP,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr


def test_electron_app_ui_has_expected_sections():
    html = INDEX_HTML.read_text()

    for text in [
        "Install / Update",
        "Run Task",
        "Chat with SafeClaw",
        "Drop files or links here",
        "WhatsApp",
        "Databases",
        "Run Read-only Query",
        "Output",
    ]:
        assert text in html


def test_electron_app_uses_existing_safeclaw_commands():
    main = MAIN_JS.read_text()
    renderer = RENDERER_JS.read_text()

    assert "install.sh" in main
    assert "safeclaw.cli" in main
    for command in ["doctor", "run", "status", "memory", "reset", "whatsapp", "service-install", "db-query"]:
        assert command in main + renderer


def test_electron_chat_supports_dropped_files_and_links():
    html = INDEX_HTML.read_text()
    preload = PRELOAD_JS.read_text()
    renderer = RENDERER_JS.read_text()
    styles = STYLES.read_text()

    assert "chatDropZone" in html
    assert "chatAttachments" in html
    assert "webUtils.getPathForFile" in preload
    assert "handleChatDrop" in renderer
    assert "Dropped attachments:" in renderer
    assert "text/uri-list" in renderer
    assert "file.text()" in renderer
    assert "textAttachmentLimit" in renderer
    assert "attachment-chip" in styles
    assert "dragging-chat" in styles


def test_electron_chat_fluidity_features_are_wired():
    html = INDEX_HTML.read_text()
    main = MAIN_JS.read_text()
    preload = PRELOAD_JS.read_text()
    renderer = RENDERER_JS.read_text()
    styles = STYLES.read_text()

    for text in [
        "sessionList",
        "chatContextBar",
        "approvalTray",
        "attachmentDrawer",
        "Run doctor",
        "Remember This",
        "Export Session",
    ]:
        assert text in html

    for text in ["list-sessions", "rename-session", "delete-session", "approve-command"]:
        assert text in main

    for text in ["sessions", "renameSession", "deleteSession", "approve"]:
        assert text in preload

    for text in [
        "refreshSessions",
        "renderApprovalCard",
        "setMessageState",
        "result-block",
        "queued",
        "needs approval",
        "failed",
        "stopped",
        "done",
        "Send as reference",
        "Include contents",
        "Outside workspace warning",
        "Huge file warning",
    ]:
        assert text in renderer + styles


def test_readme_references_mac_app_screenshots():
    text = (ROOT / "README.md").read_text()

    assert "Mac App Screenshots" in text
    assert "docs/screenshots/mac-app-setup.png" in text
    assert "docs/screenshots/mac-app-chat.png" in text
    assert "docs/screenshots/mac-app-databases.png" in text
    assert "landing-home.png" not in text


def test_mac_app_readme_documents_electron_flow():
    text = APP_README.read_text()

    assert "Electron" in text
    assert "npm install" in text
    assert "npm start" in text
    assert "npm run build:mac" in text
    assert "mac-setup/" in text
