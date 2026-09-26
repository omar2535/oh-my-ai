"""Small modal dialogs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

CSS = """
ConfirmUninstall, PromptScreen { align: center middle; }
#dialog { width: 70; height: auto; padding: 1 2; border: thick $accent; background: $surface; }
#dialog Button { margin: 1 1 0 0; }
"""


class ConfirmUninstall(ModalScreen[str | None]):
    DEFAULT_CSS = CSS
    BINDINGS = [("escape", "dismiss(None)", "Cancel")]

    def __init__(self, harness):
        super().__init__()
        self.harness = harness

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"Uninstall {self.harness.name}?")
            yield Label(f"Keeping config keeps {', '.join(self.harness.config_dirs) or 'its config'}.")
            yield Button("Uninstall, keep config", id="keep", variant="primary")
            yield Button("Uninstall + purge config & credentials", id="purge", variant="error")
            yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None if event.button.id == "cancel" else event.button.id)


class PromptScreen(ModalScreen[str | None]):
    DEFAULT_CSS = CSS
    BINDINGS = [("escape", "dismiss(None)", "Cancel")]

    def __init__(self, question: str, placeholder: str = ""):
        super().__init__()
        self.question = question
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.question)
            yield Input(placeholder=self.placeholder)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)
