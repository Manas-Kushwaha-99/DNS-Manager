import base64
import ctypes
import ipaddress
import os
import platform
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field

import flet as ft
import httpx


TEST_HOSTNAMES = [
    "google.com",
    "youtube.com",
    "facebook.com",
    "reddit.com",
    "amazon.com",
    "wikipedia.org",
    "netflix.com",
    "microsoft.com",
]

TEST_ROUNDS = 3
TIMEOUT_SECONDS = 5
TIMEOUT_PENALTY_MS = 5000


def build_dns_query(hostname: str) -> bytes:
    header = bytearray(12)
    txid = int.from_bytes(os.urandom(2), "big")
    header[0] = (txid >> 8) & 0xFF
    header[1] = txid & 0xFF
    header[2] = 0x01
    header[5] = 0x01
    labels = hostname.rstrip(".").split(".")
    qname = bytearray()
    for label in labels:
        encoded = label.encode("ascii")
        qname.append(len(encoded))
        qname.extend(encoded)
    qname.append(0)
    qtype_class = struct.pack(">HH", 1, 1)
    return bytes(header + qname + qtype_class)


def encode_dns_query_base64url(query: bytes) -> str:
    return base64.urlsafe_b64encode(query).rstrip(b"=").decode("ascii")


def _detect_doh_method(client: httpx.Client, doh_url: str) -> str | None:
    query = build_dns_query("example.com")
    try:
        response = client.post(
            doh_url,
            content=query,
            headers={
                "Content-Type": "application/dns-message",
                "Accept": "application/dns-message",
            },
        )
        if 200 <= response.status_code < 300:
            return "post"
    except Exception:
        pass
    try:
        encoded = encode_dns_query_base64url(query)
        sep = "&" if "?" in doh_url else "?"
        response = client.get(
            f"{doh_url}{sep}dns={encoded}",
            headers={"Accept": "application/dns-message"},
        )
        if 200 <= response.status_code < 300:
            return "get"
    except Exception:
        pass
    return None


def measure_doh_speed(
    client: httpx.Client, doh_url: str, hostname: str, method: str
) -> float | None:
    query = build_dns_query(hostname)
    try:
        start = time.perf_counter()
        if method == "get":
            encoded = encode_dns_query_base64url(query)
            sep = "&" if "?" in doh_url else "?"
            response = client.get(
                f"{doh_url}{sep}dns={encoded}",
                headers={"Accept": "application/dns-message"},
            )
        else:
            response = client.post(
                doh_url,
                content=query,
                headers={
                    "Content-Type": "application/dns-message",
                    "Accept": "application/dns-message",
                },
            )
        elapsed = (time.perf_counter() - start) * 1000.0
        if 200 <= response.status_code < 300:
            return elapsed
        return None
    except Exception:
        return None


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> None:
    params = " ".join(f'"{arg}"' for arg in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)


def quote_ps(value: str) -> str:
    return value.replace("'", "''")


def run_powershell(command: str) -> tuple[bool, str, str]:
    args = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-NoLogo",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
    ]

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags |= subprocess.CREATE_NO_WINDOW

    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        startupinfo=startupinfo,
        creationflags=creationflags,
    )

    return completed.returncode == 0, completed.stdout.strip(), completed.stderr.strip()


def valid_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class DNSPreset:
    name: str
    primary: str
    secondary: str
    description: str
    icon: str
    color: str
    doh_url: str = ""


@dataclass
class AppState:
    adapters: list[str] = field(default_factory=list)
    selected_adapter: str | None = None
    current_dns: list[str] = field(default_factory=list)
    busy: bool = False
    speed_results: dict = field(default_factory=dict)
    testing_speed: bool = False


class DNSService:
    def list_active_adapters(self) -> list[str]:
        primary = (
            "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
            "Select-Object -ExpandProperty Name"
        )
        ok, out, err = run_powershell(primary)
        if ok and out:
            return sorted({line.strip() for line in out.splitlines() if line.strip()})

        fallback = "Get-DnsClient | Select-Object -ExpandProperty InterfaceAlias | Sort-Object -Unique"
        ok, out, fallback_err = run_powershell(fallback)
        if ok and out:
            return sorted({line.strip() for line in out.splitlines() if line.strip()})

        raise RuntimeError(
            err or fallback_err or "Failed to enumerate network adapters"
        )

    def get_current_dns(self, adapter: str) -> list[str]:
        command = (
            "Get-DnsClientServerAddress "
            f"-InterfaceAlias '{quote_ps(adapter)}' -AddressFamily IPv4 | "
            "Select-Object -ExpandProperty ServerAddresses"
        )
        ok, out, err = run_powershell(command)
        if not ok:
            raise RuntimeError(err or "Failed to read current DNS")
        return [line.strip() for line in out.splitlines() if line.strip()]

    def set_dns(self, adapter: str, servers: list[str]) -> None:
        addresses = "(" + ",".join(f"'{quote_ps(server)}'" for server in servers) + ")"
        command = (
            "Set-DnsClientServerAddress "
            f"-InterfaceAlias '{quote_ps(adapter)}' -ServerAddresses {addresses}"
        )
        ok, _, err = run_powershell(command)
        if not ok:
            raise RuntimeError(err or "Failed to apply DNS")

    def reset_dns(self, adapter: str) -> None:
        command = (
            "Set-DnsClientServerAddress "
            f"-InterfaceAlias '{quote_ps(adapter)}' -ResetServerAddresses"
        )
        ok, _, err = run_powershell(command)
        if not ok:
            raise RuntimeError(err or "Failed to reset DNS")

    def flush_dns_cache(self) -> None:
        ok, _, err = run_powershell("Clear-DnsClientCache")
        if not ok:
            raise RuntimeError(err or "Failed to flush DNS cache")


class DNSManagerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.state = AppState()
        self.service = DNSService()
        self.presets = self.build_presets()
        self.selected_preset = self.presets[0]

        self.configure_page()
        self.build_controls()
        self.build_layout()
        self.load_adapters()

    def configure_page(self) -> None:
        self.page.title = "DNS Manager"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window.min_width = 980
        self.page.window.min_height = 760
        self.page.window.resizable = True
        self.page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=ft.Colors.CYAN_400,
                secondary=ft.Colors.BLUE_300,
                surface=ft.Colors.BLUE_GREY_900,
                background="#0B1220",
            )
        )

    def build_presets(self) -> list[DNSPreset]:
        return [
            DNSPreset(
                "Custom",
                "",
                "",
                "Use any IPv4 DNS pair you want.",
                ft.Icons.TUNE,
                ft.Colors.GREY_500,
            ),
            DNSPreset(
                "Google",
                "8.8.8.8",
                "8.8.4.4",
                "Reliable public DNS with broad reach.",
                ft.Icons.PUBLIC,
                ft.Colors.BLUE_400,
                "https://dns.google/dns-query",
            ),
            DNSPreset(
                "Cloudflare",
                "1.1.1.1",
                "1.0.0.1",
                "Fast privacy-focused resolver.",
                ft.Icons.FLASH_ON,
                ft.Colors.ORANGE_400,
                "https://cloudflare-dns.com/dns-query",
            ),
            DNSPreset(
                "Cloudflare Security",
                "1.1.1.2",
                "1.0.0.2",
                "Blocks malware and phishing domains.",
                ft.Icons.SECURITY,
                ft.Colors.ORANGE_700,
                "https://security.cloudflare-dns.com/dns-query",
            ),
            DNSPreset(
                "Quad9",
                "9.9.9.9",
                "149.112.112.112",
                "Security-oriented resolver with threat blocking.",
                ft.Icons.SHIELD,
                ft.Colors.GREEN_400,
                "https://dns.quad9.net/dns-query",
            ),
            DNSPreset(
                "OpenDNS",
                "208.67.222.222",
                "208.67.220.220",
                "Cisco public DNS with stable performance.",
                ft.Icons.BUSINESS,
                ft.Colors.PURPLE_400,
                "https://doh.opendns.com/dns-query",
            ),
            DNSPreset(
                "AdGuard",
                "94.140.14.14",
                "94.140.15.15",
                "General ad and tracker blocking DNS.",
                ft.Icons.BLOCK,
                ft.Colors.RED_400,
                "https://dns.adguard-dns.com/dns-query",
            ),
            DNSPreset(
                "CleanBrowsing",
                "185.228.168.9",
                "185.228.169.9",
                "Family-safe content filtering.",
                ft.Icons.FAMILY_RESTROOM,
                ft.Colors.LIGHT_BLUE_400,
                "https://doh.cleanbrowsing.org/doh/family-filter/",
            ),
            DNSPreset(
                "Mullvad DNS",
                "194.242.2.2",
                "194.242.2.3",
                "Privacy-first resolver from Mullvad.",
                ft.Icons.PRIVACY_TIP,
                ft.Colors.GREEN_700,
                "https://dns.mullvad.net/dns-query",
            ),
            DNSPreset(
                "DNS.Watch",
                "84.200.69.80",
                "84.200.70.40",
                "Unfiltered privacy-friendly European DNS.",
                ft.Icons.VISIBILITY,
                ft.Colors.AMBER_400,
            ),
        ]

    def build_controls(self) -> None:
        self.status_ring = ft.ProgressRing(
            width=18, height=18, stroke_width=2, visible=False
        )
        self.status_text = ft.Text("Ready", size=12, color=ft.Colors.BLUE_GREY_200)

        self.adapter_dropdown = ft.Dropdown(
            label="Network adapter",
            hint_text="Select an active network adapter",
            prefix_icon=ft.Icons.ROUTER,
            expand=True,
            on_change=self.on_adapter_change,
        )

        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Refresh adapters",
            on_click=lambda _: self.load_adapters(),
        )

        self.current_dns_label = ft.Text(
            "Current DNS will appear here after an adapter is loaded.",
            size=13,
            color=ft.Colors.BLUE_GREY_100,
        )

        self.primary_dns = ft.TextField(
            label="Primary DNS",
            hint_text="8.8.8.8",
            prefix_icon=ft.Icons.LOOKS_ONE,
            on_change=self.validate_dns_input,
            expand=True,
        )

        self.secondary_dns = ft.TextField(
            label="Secondary DNS",
            hint_text="8.8.4.4",
            prefix_icon=ft.Icons.LOOKS_TWO,
            on_change=self.validate_dns_input,
            expand=True,
        )

        self.apply_button = ft.ElevatedButton(
            "Apply DNS",
            icon=ft.Icons.CHECK_CIRCLE,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
            on_click=self.apply_dns,
        )

        self.reset_button = ft.OutlinedButton(
            "Reset to Automatic",
            icon=ft.Icons.RESTORE,
            on_click=self.reset_dns,
        )

        self.flush_button = ft.OutlinedButton(
            "Flush DNS Cache",
            icon=ft.Icons.CLEANING_SERVICES,
            on_click=self.flush_cache,
        )

        self.log_list = ft.ListView(expand=True, spacing=8, auto_scroll=True)
        self.preset_grid = ft.ResponsiveRow(run_spacing=12, spacing=12)

        self.speed_test_button = ft.ElevatedButton(
            "Speed Test",
            icon=ft.Icons.SPEED,
            style=ft.ButtonStyle(bgcolor=ft.Colors.CYAN_700, color=ft.Colors.WHITE),
            on_click=self.start_speed_test,
        )
        self.speed_test_progress = ft.Text("", size=11, color=ft.Colors.BLUE_GREY_300)

    def build_layout(self) -> None:
        header = ft.Container(
            padding=ft.padding.symmetric(horizontal=28, vertical=24),
            gradient=ft.LinearGradient(["#102038", "#142B4D", "#0E1A2B"]),
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=54,
                        height=54,
                        border_radius=18,
                        bgcolor="#16335B",
                        alignment=ft.alignment.center,
                        content=ft.Icon(
                            ft.Icons.DNS, size=30, color=ft.Colors.CYAN_300
                        ),
                    ),
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text("DNS Manager", size=30, weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    ft.Container(expand=True),
                    ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        spacing=3,
                        controls=[
                            ft.Text(
                                "Made by Manas Kushwaha",
                                size=14,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Row(
                                spacing=10,
                                controls=[self.status_ring, self.status_text],
                            ),
                        ],
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        adapter_panel = self.panel(
            title="Adapter",
            subtitle="Choose the adapter you want to update.",
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row([self.adapter_dropdown, self.refresh_button], spacing=10),
                    ft.Container(
                        padding=14,
                        border_radius=16,
                        bgcolor="#101C2F",
                        content=ft.Row(
                            spacing=12,
                            controls=[
                                ft.Icon(ft.Icons.STORAGE, color=ft.Colors.CYAN_300),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            "Current DNS",
                                            size=12,
                                            color=ft.Colors.BLUE_GREY_300,
                                        ),
                                        self.current_dns_label,
                                    ],
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )

        preset_panel = self.panel(
            title="Presets",
            subtitle="Pick a known resolver or switch to custom mode.",
            trailing=ft.Row(
                spacing=8,
                controls=[
                    self.speed_test_progress,
                    self.speed_test_button,
                ],
            ),
            content=ft.Column(controls=[self.preset_grid], spacing=0),
        )

        custom_panel = self.panel(
            title="DNS Addresses",
            subtitle="Enter IPv4 addresses manually or populate them from a preset.",
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(
                                col={"xs": 12, "md": 6}, content=self.primary_dns
                            ),
                            ft.Container(
                                col={"xs": 12, "md": 6}, content=self.secondary_dns
                            ),
                        ]
                    ),
                    ft.Row(
                        wrap=True,
                        spacing=12,
                        controls=[
                            self.apply_button,
                            self.reset_button,
                            self.flush_button,
                        ],
                    ),
                ],
            ),
        )

        log_panel = self.panel(
            title="Activity",
            subtitle="Background operations and validation messages appear here.",
            trailing=ft.IconButton(
                icon=ft.Icons.CLEAR_ALL,
                tooltip="Clear log",
                on_click=self.clear_logs,
            ),
            content=ft.Container(
                height=220,
                padding=14,
                border_radius=16,
                bgcolor="#0E1726",
                border=ft.border.all(1, "#1B2B40"),
                content=self.log_list,
            ),
        )

        content = ft.Container(
            expand=True,
            padding=ft.padding.symmetric(horizontal=24, vertical=20),
            content=ft.Column(
                expand=True,
                spacing=18,
                scroll=ft.ScrollMode.ADAPTIVE,
                controls=[adapter_panel, preset_panel, custom_panel, log_panel],
            ),
        )

        self.page.add(ft.Column(expand=True, spacing=0, controls=[header, content]))
        self.rebuild_preset_cards()
        self.set_preset(self.selected_preset, log_selection=False)
        self.add_log("Application initialized.", ft.Colors.CYAN_300)

    def panel(
        self,
        *,
        title: str,
        subtitle: str,
        content: ft.Control,
        trailing: ft.Control | None = None,
    ) -> ft.Control:
        header_row = ft.Row(
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(subtitle, size=12, color=ft.Colors.BLUE_GREY_200),
                    ],
                ),
                ft.Container(expand=True),
                trailing or ft.Container(),
            ]
        )

        return ft.Container(
            padding=20,
            border_radius=22,
            bgcolor="#121C2B",
            border=ft.border.all(1, "#1C2B3C"),
            content=ft.Column(spacing=18, controls=[header_row, content]),
        )

    def rebuild_preset_cards(self) -> None:
        self.preset_grid.controls.clear()
        for preset in self.presets:
            active = preset.name == self.selected_preset.name
            ping_text = self.state.speed_results.get(preset.name)
            ping_row = ft.Row(
                spacing=0,
                controls=[ft.Container(expand=True)],
            )
            if not preset.doh_url:
                ping_row.controls.append(
                    ft.Text(
                        "No DoH",
                        size=10,
                        color=ft.Colors.BLUE_GREY_500,
                        weight=ft.FontWeight.W_600,
                    )
                )
            elif ping_text is not None:
                avg = ping_text.get("avg")
                status = ping_text.get("status", "failed")
                if avg is not None:
                    if status == "healthy":
                        ping_color = (
                            ft.Colors.GREEN_300
                            if avg < 50
                            else (
                                ft.Colors.AMBER_300
                                if avg < 75
                                else (
                                    ft.Colors.RED_400
                                    if avg < 100
                                    else ft.Colors.RED_900
                                )
                            )
                        )
                    elif status == "partial":
                        ping_color = ft.Colors.AMBER_300
                    else:
                        ping_color = ft.Colors.RED_300
                    ping_row.controls.append(
                        ft.Text(
                            f"{avg:.1f} ms",
                            size=11,
                            color=ping_color,
                            weight=ft.FontWeight.BOLD,
                        )
                    )
                elif status == "failed":
                    ping_row.controls.append(
                        ft.Text(
                            "Failed",
                            size=11,
                            color=ft.Colors.RED_300,
                            weight=ft.FontWeight.BOLD,
                        )
                    )
            card = ft.Container(
                col={"xs": 12, "sm": 6, "lg": 4},
                ink=True,
                border_radius=18,
                padding=16,
                bgcolor="#18263A" if active else "#10192A",
                border=ft.border.all(
                    2 if active else 1, preset.color if active else "#203146"
                ),
                on_click=lambda e, selected=preset: self.set_preset(selected),
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    width=42,
                                    height=42,
                                    border_radius=14,
                                    bgcolor="#0B1524",
                                    alignment=ft.alignment.center,
                                    content=ft.Icon(preset.icon, color=preset.color),
                                ),
                                ft.Container(expand=True),
                                ft.Icon(
                                    ft.Icons.CHECK_CIRCLE
                                    if active
                                    else ft.Icons.RADIO_BUTTON_UNCHECKED,
                                    color=preset.color,
                                    size=20,
                                ),
                            ]
                        ),
                        ft.Text(preset.name, size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            preset.description, size=12, color=ft.Colors.BLUE_GREY_100
                        ),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=10, vertical=8),
                            border_radius=12,
                            bgcolor="#0B1524",
                            content=ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Text(
                                        f"Primary: {preset.primary or 'Manual input'}",
                                        size=11,
                                        color=ft.Colors.BLUE_GREY_200,
                                    ),
                                    ft.Text(
                                        f"Secondary: {preset.secondary or 'Optional'}",
                                        size=11,
                                        color=ft.Colors.BLUE_GREY_200,
                                    ),
                                ],
                            ),
                        ),
                        ping_row,
                    ],
                ),
            )
            self.preset_grid.controls.append(card)
        self.safe_update(self.preset_grid)

    def set_preset(self, preset: DNSPreset, log_selection: bool = True) -> None:
        self.selected_preset = preset
        self.primary_dns.value = preset.primary
        self.secondary_dns.value = preset.secondary
        self.primary_dns.error_text = None
        self.secondary_dns.error_text = None
        self.rebuild_preset_cards()
        self.safe_update(self.primary_dns, self.secondary_dns)
        if log_selection:
            self.add_log(f"Selected preset: {preset.name}", preset.color)

    def on_adapter_change(self, event: ft.ControlEvent) -> None:
        self.state.selected_adapter = event.control.value
        self.load_current_dns()

    def validate_dns_input(self, event: ft.ControlEvent) -> None:
        value = event.control.value.strip()
        event.control.error_text = (
            None if not value or valid_ipv4(value) else "Invalid IPv4 address"
        )
        self.safe_update(event.control)

    def load_adapters(self) -> None:
        def worker() -> None:
            self.set_busy(True, "Loading network adapters...")
            try:
                adapters = self.service.list_active_adapters()
                self.state.adapters = adapters
                self.adapter_dropdown.options = [
                    ft.dropdown.Option(adapter) for adapter in adapters
                ]

                if adapters:
                    if self.state.selected_adapter not in adapters:
                        self.state.selected_adapter = adapters[0]
                    self.adapter_dropdown.value = self.state.selected_adapter
                    self.add_log(
                        f"Loaded {len(adapters)} active adapter(s).",
                        ft.Colors.GREEN_400,
                    )
                    self.load_current_dns(in_background=True)
                else:
                    self.state.selected_adapter = None
                    self.adapter_dropdown.value = None
                    self.current_dns_label.value = "No active adapters were found."
                    self.current_dns_label.color = ft.Colors.ORANGE_300
                    self.add_log("No active adapters found.", ft.Colors.ORANGE_300)
                    self.set_busy(False, "No adapters found.")

                self.safe_update(self.adapter_dropdown, self.current_dns_label)
            except Exception as exc:
                self.add_log(f"Adapter load failed: {exc}", ft.Colors.RED_400)
                self.set_busy(False, "Adapter load failed.")

        threading.Thread(target=worker, daemon=True).start()

    def load_current_dns(self, in_background: bool = False) -> None:
        adapter = self.state.selected_adapter
        if not adapter:
            self.current_dns_label.value = (
                "Select an adapter to inspect its DNS settings."
            )
            self.current_dns_label.color = ft.Colors.BLUE_GREY_100
            self.safe_update(self.current_dns_label)
            return

        def worker() -> None:
            if not in_background:
                self.set_busy(True, f"Reading DNS for {adapter}...")
            try:
                dns_servers = self.service.get_current_dns(adapter)
                self.state.current_dns = dns_servers
                if dns_servers:
                    self.current_dns_label.value = ", ".join(dns_servers)
                    self.current_dns_label.color = ft.Colors.GREEN_300
                else:
                    self.current_dns_label.value = "Automatic DNS (DHCP)"
                    self.current_dns_label.color = ft.Colors.CYAN_300
                self.safe_update(self.current_dns_label)
                self.set_busy(False, "Loaded Network adaptor")
            except Exception as exc:
                self.current_dns_label.value = f"Failed to read DNS: {exc}"
                self.current_dns_label.color = ft.Colors.RED_300
                self.safe_update(self.current_dns_label)
                self.add_log(f"DNS read failed: {exc}", ft.Colors.RED_400)
                self.set_busy(False, "DNS read failed.")

        threading.Thread(target=worker, daemon=True).start()

    def apply_dns(self, _event: ft.ControlEvent) -> None:
        adapter = self.state.selected_adapter
        if not adapter:
            self.show_error("Select a network adapter first.")
            return

        primary = self.primary_dns.value.strip()
        secondary = self.secondary_dns.value.strip()

        if not primary:
            self.show_error("Primary DNS is required.")
            return
        if not valid_ipv4(primary):
            self.show_error("Primary DNS must be a valid IPv4 address.")
            return
        if secondary and not valid_ipv4(secondary):
            self.show_error("Secondary DNS must be a valid IPv4 address.")
            return

        servers = [primary] + ([secondary] if secondary else [])

        def worker() -> None:
            self.set_busy(True, f"Applying DNS to {adapter}...")
            try:
                self.service.set_dns(adapter, servers)
                self.add_log(
                    f"Applied DNS to {adapter}: {', '.join(servers)}",
                    ft.Colors.GREEN_400,
                )
                self.show_success("DNS settings applied successfully.")
                self.load_current_dns(in_background=True)
            except Exception as exc:
                self.add_log(f"DNS apply failed: {exc}", ft.Colors.RED_400)
                self.show_error(f"Failed to apply DNS: {exc}")
                self.set_busy(False, "Apply failed.")

        threading.Thread(target=worker, daemon=True).start()

    def reset_dns(self, _event: ft.ControlEvent) -> None:
        adapter = self.state.selected_adapter
        if not adapter:
            self.show_error("Select a network adapter first.")
            return

        def worker() -> None:
            self.set_busy(True, f"Resetting DNS for {adapter}...")
            try:
                self.service.reset_dns(adapter)
                self.add_log(
                    f"Reset DNS for {adapter} back to automatic.", ft.Colors.GREEN_400
                )
                self.show_success("DNS has been reset to automatic.")
                self.load_current_dns(in_background=True)
            except Exception as exc:
                self.add_log(f"DNS reset failed: {exc}", ft.Colors.RED_400)
                self.show_error(f"Failed to reset DNS: {exc}")
                self.set_busy(False, "Reset failed.")

        threading.Thread(target=worker, daemon=True).start()

    def flush_cache(self, _event: ft.ControlEvent) -> None:
        def worker() -> None:
            self.set_busy(True, "Flushing DNS cache...")
            try:
                self.service.flush_dns_cache()
                self.add_log("Flushed Windows DNS cache.", ft.Colors.GREEN_400)
                self.show_success("DNS cache flushed successfully.")
                self.set_busy(False, "DNS cache flushed.")
            except Exception as exc:
                self.add_log(f"DNS cache flush failed: {exc}", ft.Colors.RED_400)
                self.show_error(f"Failed to flush DNS cache: {exc}")
                self.set_busy(False, "Flush failed.")

        threading.Thread(target=worker, daemon=True).start()

    def start_speed_test(self, _event: ft.ControlEvent) -> None:
        if self.state.testing_speed:
            return
        self.state.testing_speed = True
        self.state.speed_results.clear()
        self.speed_test_button.disabled = True
        self.speed_test_button.text = "Testing..."
        self.speed_test_progress.value = "Warming up..."
        self.speed_test_progress.color = ft.Colors.BLUE_GREY_300
        self.rebuild_preset_cards()
        self.safe_update(self.speed_test_button, self.speed_test_progress)

        def worker() -> None:
            try:
                testable = [p for p in self.presets if p.doh_url]
                total = len(testable)

                for i, preset in enumerate(testable):
                    progress_text = f"Warming up {preset.name} ({i + 1}/{total})..."
                    self.page.run_thread(
                        lambda t=progress_text: self._update_test_progress(t)
                    )

                    try:
                        client = httpx.Client(
                            timeout=httpx.Timeout(TIMEOUT_SECONDS),
                            follow_redirects=True,
                            http2=True,
                        )
                        method = _detect_doh_method(client, preset.doh_url)
                        if method is None:
                            self.state.speed_results[preset.name] = {
                                "avg": None,
                                "status": "failed",
                                "success": 0,
                                "total": len(TEST_HOSTNAMES) * TEST_ROUNDS,
                            }
                            client.close()
                            self.page.run_thread(
                                lambda: self.rebuild_preset_cards()
                            )
                            continue

                        for _ in range(2):
                            measure_doh_speed(
                                client, preset.doh_url, "example.com", method
                            )
                    except Exception:
                        self.state.speed_results[preset.name] = {
                            "avg": None,
                            "status": "failed",
                            "success": 0,
                            "total": len(TEST_HOSTNAMES) * TEST_ROUNDS,
                        }
                        self.page.run_thread(
                            lambda: self.rebuild_preset_cards()
                        )
                        continue

                    all_rounds: dict[str, list[float]] = {
                        h: [] for h in TEST_HOSTNAMES
                    }

                    for round_num in range(1, TEST_ROUNDS + 1):
                        progress_text = (
                            f"Testing {preset.name} "
                            f"({i + 1}/{total}) — Round {round_num}/{TEST_ROUNDS}"
                        )
                        self.page.run_thread(
                            lambda t=progress_text: self._update_test_progress(t)
                        )

                        for hostname in TEST_HOSTNAMES:
                            ms = measure_doh_speed(
                                client, preset.doh_url, hostname, method
                            )
                            if ms is not None:
                                all_rounds[hostname].append(ms)

                    client.close()

                    hostname_medians = []
                    total_queries = len(TEST_HOSTNAMES) * TEST_ROUNDS
                    success_count = 0

                    for hostname, times in all_rounds.items():
                        if times:
                            times.sort()
                            mid = len(times) // 2
                            if len(times) % 2 == 0:
                                median_val = (times[mid - 1] + times[mid]) / 2
                            else:
                                median_val = times[mid]
                            hostname_medians.append(median_val)
                            success_count += len(times)

                    if not hostname_medians:
                        self.state.speed_results[preset.name] = {
                            "avg": None,
                            "status": "failed",
                            "success": 0,
                            "total": total_queries,
                        }
                    else:
                        avg = sum(hostname_medians) / len(hostname_medians)
                        fail_count = total_queries - success_count
                        if fail_count == 0:
                            status = "healthy"
                        else:
                            status = "partial"
                        self.state.speed_results[preset.name] = {
                            "avg": avg,
                            "status": status,
                            "success": success_count,
                            "total": total_queries,
                        }

                    self.page.run_thread(lambda: self.rebuild_preset_cards())

                tested_count = sum(
                    1
                    for p in testable
                    if self.state.speed_results.get(p.name, {}).get("status")
                    != "failed"
                )
                self.page.run_thread(
                    lambda: self._finish_speed_test(tested_count, total)
                )
            except Exception as exc:
                self.page.run_thread(
                    lambda: self._finish_speed_test(0, total, str(exc))
                )

        threading.Thread(target=worker, daemon=True).start()

    def _update_test_progress(self, text: str) -> None:
        self.speed_test_progress.value = text
        self.safe_update(self.speed_test_progress)

    def _finish_speed_test(
        self, tested_count: int, total: int, error: str | None = None
    ) -> None:
        self.state.testing_speed = False
        self.speed_test_button.disabled = False
        self.speed_test_button.text = "Speed Test"

        if error:
            self.speed_test_progress.value = f"Error: {error}"
            self.speed_test_progress.color = ft.Colors.RED_300
            self.add_log(f"Speed test failed: {error}", ft.Colors.RED_400)
        else:
            self.speed_test_progress.value = f"Tested {tested_count}/{total} servers"
            self.speed_test_progress.color = ft.Colors.GREEN_300
            self.add_log(
                f"Speed test complete: {tested_count}/{total} servers tested.",
                ft.Colors.GREEN_400,
            )

        self.rebuild_preset_cards()
        self.safe_update(self.speed_test_button, self.speed_test_progress)

    def set_busy(self, busy: bool, status: str) -> None:
        self.state.busy = busy
        self.status_ring.visible = busy
        self.status_text.value = status
        self.apply_button.disabled = busy
        self.reset_button.disabled = busy
        self.flush_button.disabled = busy
        self.refresh_button.disabled = busy
        self.adapter_dropdown.disabled = busy
        self.speed_test_button.disabled = busy or self.state.testing_speed
        self.safe_update(
            self.status_ring,
            self.status_text,
            self.apply_button,
            self.reset_button,
            self.flush_button,
            self.refresh_button,
            self.adapter_dropdown,
            self.speed_test_button,
        )

    def add_log(self, message: str, color: str | None = None) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_list.controls.append(
            ft.Container(
                padding=ft.padding.symmetric(vertical=4),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Text(
                            f"[{timestamp}]", size=11, color=ft.Colors.BLUE_GREY_400
                        ),
                        ft.Text(
                            message,
                            size=12,
                            color=color or ft.Colors.BLUE_GREY_100,
                            expand=True,
                        ),
                    ],
                ),
            )
        )
        if len(self.log_list.controls) > 120:
            self.log_list.controls.pop(0)
        self.safe_update(self.log_list)

    def clear_logs(self, _event: ft.ControlEvent) -> None:
        self.log_list.controls.clear()
        self.add_log("Activity log cleared.", ft.Colors.CYAN_300)

    def show_success(self, message: str) -> None:
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message), bgcolor=ft.Colors.GREEN_700
        )
        self.page.snack_bar.open = True
        self.safe_update(self.page)

    def show_error(self, message: str) -> None:
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message), bgcolor=ft.Colors.RED_700
        )
        self.page.snack_bar.open = True
        self.safe_update(self.page)

    def safe_update(self, *controls: ft.Control) -> None:
        try:
            if not controls:
                self.page.update()
                return
            for control in controls:
                if control is self.page:
                    self.page.update()
                else:
                    control.update()
        except Exception:
            pass


def main(page: ft.Page) -> None:
    DNSManagerApp(page)


if __name__ == "__main__":
    if platform.system() != "Windows":
        print("This tool supports Windows only.")
        sys.exit(1)

    if not is_admin():
        relaunch_as_admin()
        sys.exit(0)

    ft.app(target=main)
