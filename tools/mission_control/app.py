"""Minimal Textual-based TUI prototype for Mission Control

This is a small PoC that provides the basic pane layout and sample data.
"""

from rich.text import Text

# Textual imports are optional; provide minimal fallbacks so the module can be
# imported in environments without the TUI runtime (e.g., CI / tests).
try:
    from textual.app import App
    from textual.widgets import Header, Footer, Static
    from textual.containers import Horizontal, Vertical
except Exception:  # pragma: no cover - optional runtime dependency

    class App:  # lightweight fallback
        def run(self):
            print("Textual is not installed. Install it with `uv add textual` to run the TUI.")

    class Header:
        pass

    class Footer:
        pass

    class Static:
        def __init__(self, *args, **kwargs):
            pass

    class Horizontal:
        pass

    class Vertical:
        pass


# OpenTelemetry tracer fallback
try:
    from epstein.telemetry import init_tracer, get_tracer

    init_tracer()
except Exception:  # pragma: no cover - optional runtime dependency
    import contextlib

    def get_tracer(name: str | None = None):
        class Noop:
            def start_as_current_span(self, *a, **kw):
                return contextlib.nullcontext()

        return Noop()


class Pane(Static):
    def __init__(self, title: str, content: str = ""):
        super().__init__()
        self.title = title
        self.content = content

    def render(self) -> Text:
        return Text.from_markup(self.content)


class MissionControlApp(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    """

    async def on_mount(self):
        await self.view.dock(Header(), edge="top")
        await self.view.dock(Footer(), edge="bottom")

        left = Vertical()
        right = Vertical()

        self.tasks_pane = Pane(
            "Tasks", content="[bold]No tasks loaded[/bold]\nUse the CLI to add tasks."
        )
        self.agents_pane = Pane("Agents", content="[yellow]Loading agents...[/yellow]")
        self.logs_pane = Pane("Logs", content="[green]Logs will stream here...[/green]")
        self.cmd_pane = Pane("Command", content="Type a command... (stub)")

        await left.mount(self.tasks_pane)
        await left.mount(self.agents_pane)

        await right.mount(self.logs_pane)
        await right.mount(self.cmd_pane)

        await self.view.dock(left, edge="left", size=40)
        await self.view.dock(right, edge="right")

        # Start orchestrator client and poll status every 5 seconds
        try:
            self._orch_client = OrchestratorClient()
            tracer = get_tracer("mission-control-ui")

            async def _update_status_once():
                with tracer.start_as_current_span("ui_poll_status"):
                    status = await self._orch_client.get_system_status()
                    agents = status.get("agents", {})
                    text_lines = []
                    for name, info in agents.items():
                        st = info.get("status") if isinstance(info, dict) else str(info)
                        text_lines.append(f"{name}: {st}")
                    self.agents_pane.content = "\n".join(text_lines) or "No agents"
                    await self.agents_pane.refresh()

            # Use Textual's set_interval if available, otherwise schedule periodic task
            try:
                self.set_interval(5.0, lambda: self.call_later(_update_status_once))
            except Exception:
                # Fallback: schedule an asyncio task
                self.call_later(lambda: self.app_background_task(_update_status_once))
        except Exception:
            # Not fatal: UI can still run without orchestrator
            pass

    async def app_background_task(self, coro):
        # Helper to run a one-off coroutine
        try:
            await coro()
        except Exception:
            pass

        # Start background polling of orchestrator status
        try:
            from .orchestrator_client import OrchestratorClient

            self.orch = OrchestratorClient()
            self.set_interval(5.0, self._poll_status)
        except Exception:
            # Orchestrator not available in this environment
            pass

    async def _poll_status(self):
        try:
            # Add a small trace around the poll
            try:
                from epstein.telemetry import get_tracer

                tracer = get_tracer("mission_control.ui")
            except Exception:
                tracer = None

            if tracer:
                with tracer.start_as_current_span("ui.poll_status"):
                    status = await self.orch.get_status()
            else:
                status = await self.orch.get_status()

            agents = status.get("agents", {})
            tasks = status.get("tasks", {})

            agents_lines = [f"{k}: {v.get('status', 'unknown')}" for k, v in agents.items()]
            tasks_lines = [
                f"total:{tasks.get('total', 0)} pending:{tasks.get('pending', 0)} running:{tasks.get('running', 0)} completed:{tasks.get('completed', 0)} failed:{tasks.get('failed', 0)}"
            ]

            self.agents_pane.content = "\n".join(agents_lines) or "No agents"
            self.tasks_pane.content = "\n".join(tasks_lines)

            await self.agents_pane.refresh()
            await self.tasks_pane.refresh()
        except Exception as e:
            # don't crash the UI on errors
            self.logs_pane.content += f"\n[red]Error polling orchestrator: {e}[/red]"
            await self.logs_pane.refresh()


def main():
    app = MissionControlApp()
    app.run()


if __name__ == "__main__":
    main()
