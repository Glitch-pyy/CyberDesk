from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional

from serial import Serial

from cyberdesk_client import (
    DeviceConnection,
    connect_to_cyberdesk,
    send_command,
)

from desktop_stream import build_desktop_update_command
from system_metrics import (
    SystemMetrics,
    collect_system_metrics,
)


WINDOW_TITLE = "CyberDesk Control Panel"
WINDOW_WIDTH = 760
WINDOW_HEIGHT = 620

METRICS_UPDATE_INTERVAL_SECONDS = 2.0


class CyberDeskControlPanel:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
        )
        self.root.minsize(680, 460)

        self.device: Optional[DeviceConnection] = None
        self.connection_thread: Optional[
            threading.Thread
        ] = None

        self.metrics_thread: Optional[
            threading.Thread
        ] = None

        self.metrics_stop_event = threading.Event()
        self.serial_lock = threading.Lock()

        self.event_queue: queue.Queue[
            tuple[str, object]
        ] = queue.Queue()

        self.connection_status = tk.StringVar(
            value="Disconnected"
        )
        self.port_status = tk.StringVar(
            value="Port: —"
        )
        self.current_page = tk.StringVar(
            value="Page: —"
        )
        self.stream_status = tk.StringVar(
            value="Stream stopped"
        )

        self.cpu_status = tk.StringVar(
            value="—%"
        )

        self.memory_status = tk.StringVar(
            value="—%"
        )

        self.battery_status = tk.StringVar(
            value="—"
        )

        self.host_status = tk.StringVar(
            value="—"
        )

        self._configure_styles()
        self._build_interface()
        self._set_connected_state(False)

        self.root.after(100, self._process_events)
        self.root.protocol(
            "WM_DELETE_WINDOW",
            self._on_close,
        )

    def _configure_styles(self) -> None:
        self.background_color = "#f3f4f6"
        self.card_color = "#ffffff"
        self.text_color = "#111827"
        self.secondary_text_color = "#6b7280"
        self.accent_color = "#2563eb"

        self.root.configure(
            background=self.background_color
        )

    def _build_interface(self) -> None:
        main_frame = tk.Frame(
            self.root,
            background=self.background_color,
            padx=20,
            pady=20,
        )
        main_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        # Header
        header_frame = tk.Frame(
            main_frame,
            background=self.background_color,
        )
        header_frame.pack(
            fill=tk.X,
            pady=(0, 18),
        )

        tk.Label(
            header_frame,
            text="CyberDesk",
            background=self.background_color,
            foreground=self.text_color,
            font=("Helvetica", 22, "bold"),
        ).pack(side=tk.LEFT)

        self.status_label = tk.Label(
            header_frame,
            textvariable=self.connection_status,
            background=self.background_color,
            foreground=self.secondary_text_color,
            font=("Helvetica", 12),
        )
        self.status_label.pack(side=tk.RIGHT)

        # Connection card
        connection_frame = tk.LabelFrame(
            main_frame,
            text="Device Connection",
            background=self.card_color,
            foreground=self.text_color,
            font=("Helvetica", 11, "bold"),
            padx=14,
            pady=14,
        )
        connection_frame.pack(
            fill=tk.X,
            pady=(0, 14),
        )

        tk.Label(
            connection_frame,
            textvariable=self.port_status,
            background=self.card_color,
            foreground=self.text_color,
            font=("Helvetica", 11),
        ).pack(
            side=tk.LEFT,
            padx=(0, 18),
        )

        tk.Label(
            connection_frame,
            textvariable=self.current_page,
            background=self.card_color,
            foreground=self.text_color,
            font=("Helvetica", 11),
        ).pack(side=tk.LEFT)

        self.connect_button = tk.Button(
            connection_frame,
            text="Connect",
            command=self._start_connection,
            background=self.accent_color,
            foreground="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Helvetica", 11, "bold"),
            padx=18,
            pady=7,
            borderwidth=0,
            highlightthickness=0,
        )
        self.connect_button.pack(side=tk.RIGHT)

        self.disconnect_button = tk.Button(
            connection_frame,
            text="Disconnect",
            command=self._disconnect,
            background="#e5e7eb",
            foreground=self.text_color,
            activebackground="#d1d5db",
            font=("Helvetica", 11),
            padx=16,
            pady=7,
            borderwidth=0,
            highlightthickness=0,
        )
        self.disconnect_button.pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        # Page controls
        page_frame = tk.LabelFrame(
            main_frame,
            text="Display Pages",
            background=self.card_color,
            foreground=self.text_color,
            font=("Helvetica", 11, "bold"),
            padx=14,
            pady=14,
        )
        page_frame.pack(
            fill=tk.X,
            pady=(0, 14),
        )

        for column in range(4):
            page_frame.grid_columnconfigure(
                column,
                weight=1,
            )

        self.page_buttons = []

        page_definitions = [
            ("Clock", "PAGE_CLOCK"),
            ("System", "PAGE_SYSTEM"),
            ("Desktop", "PAGE_DESKTOP"),
            ("Device Info", "PAGE_INFO"),
        ]

        for column, (label, command) in enumerate(
            page_definitions
        ):
            button = tk.Button(
                page_frame,
                text=label,
                command=lambda value=command: (
                    self._send_page_command(value)
                ),
                background="#e5e7eb",
                foreground=self.text_color,
                activebackground="#dbeafe",
                font=("Helvetica", 11),
                padx=12,
                pady=10,
                borderwidth=0,
                highlightthickness=0,
            )

            button.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=5,
            )

            self.page_buttons.append(button)

        # Desktop metrics
        metrics_frame = tk.LabelFrame(
            main_frame,
            text="Desktop Metrics",
            background=self.card_color,
            foreground=self.text_color,
            font=("Helvetica", 11, "bold"),
            padx=14,
            pady=14,
        )
        metrics_frame.pack(
            fill=tk.X,
            pady=(0, 14),
        )

        for column in range(4):
            metrics_frame.grid_columnconfigure(
                column,
                weight=1,
            )

        metric_definitions = [
            ("CPU", self.cpu_status),
            ("Memory", self.memory_status),
            ("Battery", self.battery_status),
            ("Host", self.host_status),
        ]

        for column, (
            metric_name,
            metric_variable,
        ) in enumerate(metric_definitions):
            card = tk.Frame(
                metrics_frame,
                background="#f9fafb",
                padx=12,
                pady=10,
                highlightbackground="#d1d5db",
                highlightthickness=1,
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=5,
            )

            tk.Label(
                card,
                text=metric_name,
                background="#f9fafb",
                foreground=self.secondary_text_color,
                font=("Helvetica", 10),
            ).pack()

            tk.Label(
                card,
                textvariable=metric_variable,
                background="#f9fafb",
                foreground=self.text_color,
                font=("Helvetica", 16, "bold"),
            ).pack(pady=(5, 0))

        stream_controls = tk.Frame(
            metrics_frame,
            background=self.card_color,
        )
        stream_controls.grid(
            row=1,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(14, 0),
        )

        tk.Label(
            stream_controls,
            textvariable=self.stream_status,
            background=self.card_color,
            foreground=self.secondary_text_color,
            font=("Helvetica", 11),
        ).pack(side=tk.LEFT)

        self.start_stream_button = tk.Button(
            stream_controls,
            text="Start Stream",
            command=self._start_metrics_stream,
            background="#059669",
            foreground="#ffffff",
            activebackground="#047857",
            activeforeground="#ffffff",
            font=("Helvetica", 11, "bold"),
            padx=16,
            pady=7,
            borderwidth=0,
            highlightthickness=0,
        )
        self.start_stream_button.pack(side=tk.RIGHT)

        self.stop_stream_button = tk.Button(
            stream_controls,
            text="Stop Stream",
            command=self._stop_metrics_stream,
            background="#e5e7eb",
            foreground=self.text_color,
            activebackground="#d1d5db",
            font=("Helvetica", 11),
            padx=16,
            pady=7,
            borderwidth=0,
            highlightthickness=0,
        )
        self.stop_stream_button.pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        # Communication log
        log_frame = tk.LabelFrame(
            main_frame,
            text="Communication Log",
            background=self.card_color,
            foreground=self.text_color,
            font=("Helvetica", 11, "bold"),
            padx=10,
            pady=10,
        )
        log_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.log_text = tk.Text(
            log_frame,
            height=14,
            wrap=tk.WORD,
            state=tk.DISABLED,
            background="#111827",
            foreground="#e5e7eb",
            insertbackground="#ffffff",
            font=("Menlo", 11),
            relief=tk.FLAT,
            borderwidth=0,
            padx=10,
            pady=10,
        )
        self.log_text.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        scrollbar = tk.Scrollbar(
            log_frame,
            orient=tk.VERTICAL,
            command=self.log_text.yview,
        )
        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y,
        )

        self.log_text.configure(
            yscrollcommand=scrollbar.set
        )

    def _set_connected_state(
        self,
        connected: bool,
    ) -> None:
        page_state = (
            tk.NORMAL
            if connected
            else tk.DISABLED
        )

        for button in self.page_buttons:
            button.configure(state=page_state)

        self.disconnect_button.configure(
            state=(
                tk.NORMAL
                if connected
                else tk.DISABLED
            )
        )

        self.connect_button.configure(
            state=(
                tk.DISABLED
                if connected
                else tk.NORMAL
            )
        )

        self.start_stream_button.configure(
            state=(
                tk.NORMAL
                if connected
                else tk.DISABLED
            )
        )

        self.stop_stream_button.configure(
            state=tk.DISABLED
        )

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(
            tk.END,
            f"{message}\n",
        )
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _start_connection(self) -> None:
        if (
            self.connection_thread is not None
            and self.connection_thread.is_alive()
        ):
            return

        self.connection_status.set("Connecting…")
        self.connect_button.configure(
            state=tk.DISABLED
        )
        self._append_log(
            "Searching for CyberDesk..."
        )

        self.connection_thread = threading.Thread(
            target=self._connection_worker,
            daemon=True,
        )
        self.connection_thread.start()

    def _connection_worker(self) -> None:
        try:
            device = connect_to_cyberdesk()

            if device is None:
                self.event_queue.put(
                    (
                        "connection_failed",
                        "CyberDesk was not found.",
                    )
                )
                return

            self.event_queue.put(
                ("connected", device)
            )

        except Exception as error:
            self.event_queue.put(
                (
                    "connection_failed",
                    str(error),
                )
            )

    def _send_page_command(
        self,
        command: str,
    ) -> None:
        if self.device is None:
            return

        thread = threading.Thread(
            target=self._command_worker,
            args=(command,),
            daemon=True,
        )
        thread.start()

    def _command_worker(
        self,
        command: str,
    ) -> None:
        if self.device is None:
            return

        try:
            with self.serial_lock:
                response = send_command(
                    self.device.serial,
                    command,
                    wait_seconds=0.4,
                )

            self.event_queue.put(
                (
                    "command_response",
                    (command, response),
                )
            )

        except Exception as error:
            self.event_queue.put(
                (
                    "connection_lost",
                    str(error),
                )
            )

    def _handle_command_response(
        self,
        command: str,
        response: list[str],
    ) -> None:
        self._append_log(f"> {command}")

        for line in response:
            self._append_log(line)

            if line.startswith("OK:PAGE:"):
                page_name = line.split(
                    ":",
                    maxsplit=2,
                )[-1]

                self.current_page.set(
                    f"Page: {page_name}"
                )
            elif line.startswith("PAGE:"):
                page_name = line.split(
                    ":",
                    maxsplit=1,
                )[-1]

                self.current_page.set(
                    f"Page: {page_name}"
                )

    def _start_metrics_stream(self) -> None:
        if self.device is None:
            return

        if (
            self.metrics_thread is not None
            and self.metrics_thread.is_alive()
        ):
            return

        self.metrics_stop_event.clear()

        self.stream_status.set("Stream running")
        self.start_stream_button.configure(
            state=tk.DISABLED
        )
        self.stop_stream_button.configure(
            state=tk.NORMAL
        )

        self._append_log(
            "Desktop metrics stream started."
        )

        self.metrics_thread = threading.Thread(
            target=self._metrics_worker,
            daemon=True,
        )
        self.metrics_thread.start()

    def _stop_metrics_stream(self) -> None:
        self.metrics_stop_event.set()

        self.stream_status.set("Stream stopped")

        self.stop_stream_button.configure(
            state=tk.DISABLED
        )

        if self.device is not None:
            self.start_stream_button.configure(
                state=tk.NORMAL
            )

        self._append_log(
            "Desktop metrics stream stopped."
        )

    def _metrics_worker(self) -> None:
        while not self.metrics_stop_event.is_set():
            if self.device is None:
                break

            try:
                metrics = collect_system_metrics()

                command = build_desktop_update_command(
                    metrics
                )

                with self.serial_lock:
                    response = send_command(
                        self.device.serial,
                        command,
                        wait_seconds=0.4,
                    )

                if "OK:DESKTOP_UPDATE" not in response:
                    raise RuntimeError(
                        "ESP32 rejected desktop update."
                    )

                self.event_queue.put(
                    (
                        "metrics_update",
                        (metrics, response),
                    )
                )

            except Exception as error:
                self.event_queue.put(
                    (
                        "metrics_error",
                        str(error),
                    )
                )
                break

            self.metrics_stop_event.wait(
                METRICS_UPDATE_INTERVAL_SECONDS
            )

    def _handle_metrics_update(
        self,
        metrics: SystemMetrics,
        response: list[str],
    ) -> None:
        self.cpu_status.set(
            f"{metrics.cpu_percent:.1f}%"
        )

        self.memory_status.set(
            f"{metrics.memory_percent:.1f}%"
        )

        if metrics.battery_percent is None:
            self.battery_status.set("N/A")
        else:
            power_label = (
                "AC"
                if metrics.power_plugged
                else "BAT"
            )

            self.battery_status.set(
                f"{metrics.battery_percent}% {power_label}"
            )

        host_name = metrics.hostname

        if len(host_name) > 18:
            host_name = f"{host_name[:15]}..."

        self.host_status.set(host_name)

        self._append_log(
            "Desktop update: "
            f"CPU {metrics.cpu_percent:.1f}% | "
            f"MEM {metrics.memory_percent:.1f}%"
        )

    def _disconnect(self) -> None:
        self.metrics_stop_event.set()

        if self.device is not None:
            try:
                self.device.serial.close()
            except Exception:
                pass

        self.device = None
        self.connection_status.set(
            "Disconnected"
        )
        self.port_status.set("Port: —")
        self.current_page.set("Page: —")
        self.stream_status.set("Stream stopped")
        self.cpu_status.set("—%")
        self.memory_status.set("—%")
        self.battery_status.set("—")
        self.host_status.set("—")

        self._set_connected_state(False)
        self._append_log(
            "Serial connection closed."
        )

    def _process_events(self) -> None:
        try:
            while True:
                event_name, payload = (
                    self.event_queue.get_nowait()
                )

                if event_name == "connected":
                    device = payload

                    if not isinstance(
                        device,
                        DeviceConnection,
                    ):
                        continue

                    self.device = device
                    self.connection_status.set(
                        "Connected"
                    )
                    self.port_status.set(
                        f"Port: {device.port}"
                    )
                    self._set_connected_state(True)
                    self._append_log(
                        f"Connected to {device.port}"
                    )

                    self._send_page_command(
                        "GET_STATUS"
                    )

                elif event_name == "metrics_update":
                    metrics, response = payload

                    if isinstance(metrics, SystemMetrics):
                        self._handle_metrics_update(
                            metrics,
                            response,
                        )

                elif event_name == "metrics_error":
                    self._append_log(
                        f"Metrics stream error: {payload}"
                    )

                    self._stop_metrics_stream()

                elif event_name == (
                    "connection_failed"
                ):
                    self.connection_status.set(
                        "Connection failed"
                    )
                    self.connect_button.configure(
                        state=tk.NORMAL
                    )
                    self._append_log(
                        str(payload)
                    )

                elif event_name == (
                    "command_response"
                ):
                    command, response = payload

                    self._handle_command_response(
                        command,
                        response,
                    )

                elif event_name == (
                    "connection_lost"
                ):
                    self._append_log(
                        f"Connection lost: {payload}"
                    )
                    self._disconnect()

        except queue.Empty:
            pass

        self.root.after(
            100,
            self._process_events,
        )

    def _on_close(self) -> None:
        self._disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    CyberDeskControlPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()