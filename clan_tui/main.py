import argparse
import asyncio
import json
import os
import re
import subprocess

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Collapsible, Footer, ListItem, ListView, Log


async def ping(host: str) -> float:
    proc = await asyncio.create_subprocess_shell(
        f"ping -c1 -q {host}",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    match = re.search(r"=.*/(?P<avg>.*)/.*", stdout.decode())
    if match:
        return float(match.group("avg"))
    else:
        return -1


def get_machines() -> list[str]:
    flake_show = json.loads(
        subprocess.run(
            ["nix", "flake", "show", "--json"], capture_output=True, text=True
        ).stdout
    )
    machines = list(flake_show["nixosConfigurations"].keys())
    return machines


class Machine:
    def __init__(self, name):
        self.name = name
        self.ping = "pinging...."
        self.log = Log()
        self.deploying = False
        self.log.styles.height = 10
        self.collapsible = Collapsible(
            self.log, collapsed=True, title=f"{name} {self.ping}"
        )
        self.list_item = ListItem(self.collapsible)
        self.list_item.machine = self

    def __str__(self):
        return self.name

    async def update_ping(self):
        self.ping = await ping(self.name)
        if self.ping == -1:
            self.collapsible.title = f"{self.name} --OFFLINE--"
        else:
            self.collapsible.title = f"{self.name} {self.ping}ms"

    async def update_machine(self, command: str):
        self.deploying = True
        env = os.environ.copy()
        env["target"] = self.name
        proc = await asyncio.create_subprocess_exec(
            "/bin/sh",
            "-c",
            command,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def read_stream(stream):
            while True:
                line = await stream.readline()
                if not line:
                    break
                self.log.write(line.decode())

        await asyncio.gather(
            read_stream(proc.stdout),
            read_stream(proc.stderr),
        )
        self.deploying = False


class FlakeDeployApp(App[None]):
    """An example of collapsible container."""

    BINDINGS = [
        ("q", "quit", "Quit Application"),
        ("c", "collapse_or_expand(True)", "Collapse All"),
        ("e", "collapse_or_expand(False)", "Expand All"),
        ("u", "update()", "Update Machine"),
    ]

    def compose(self) -> ComposeResult:
        """Compose app with collapsible containers."""
        yield Footer()
        self.machines_view = ListView()
        yield Container(self.machines_view)

    async def on_mount(self):
        """Called when the app is first mounted to the screen."""
        self.machines: dict[str, Machine] = {}
        for machine in get_machines():
            self.machines[machine] = Machine(machine)
            self.machines_view.append(self.machines[machine].list_item)
        _ = self.update_ping_forever()

    @work(exclusive=True)
    async def update_ping_forever(self) -> None:
        while True:
            pings = []
            for machine in self.machines.values():
                pings.append(machine.update_ping())
            asyncio.gather(*pings)
            await asyncio.sleep(5)

    def action_quit(self) -> None:
        self.exit()

    def action_collapse_or_expand(self, collapse: bool) -> None:
        for child in self.walk_children(Collapsible):
            child.collapsed = collapse

    async def action_update(self) -> None:
        machine = self.machines_view.highlighted_child.machine
        if not machine.deploying:
            machine.log.write("Updating...\n")
            asyncio.create_task(machine.update_machine(self.cli_args.deploy_command))

    def on_list_view_selected(self, event: ListView.Selected):
        """Show details of the selected machine."""
        machine_item = event.item
        machine_item.children[0].collapsed = not machine_item.children[0].collapsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deploy-command",
        type=str,
        default="nix run git+https://git.clan.lol/clan/clan-core -- machines update $target",
        help="Command to deploy a machine, the target machine is passed as an environment variable 'target'",
    )
    args = parser.parse_args()
    app = FlakeDeployApp()
    app.cli_args = args
    app.run()


if __name__ == "__main__":
    main()
