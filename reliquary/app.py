"""CustomTkinter GUI for Reliquary."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from reliquary.vault import (
    InvalidMasterPasswordError,
    SecretAlreadyExistsError,
    SecretNotFoundError,
    Vault,
    VaultError,
    VaultLockedError,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class ReliquaryApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Reliquary")
        self.geometry("960x600")
        self.minsize(800, 500)

        self.vault = Vault()
        self._selected_path: str | None = None
        self._busy = False

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True, padx=16, pady=16)

        if self.vault.is_initialized():
            self._show_login()
        else:
            self._show_create_vault()

    def _clear_container(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self.config(cursor="watch")
        else:
            self.config(cursor="")

    def _run_async(
        self,
        work: Callable[[], None],
        on_success: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        if self._busy:
            return

        self._set_busy(True)

        def runner() -> None:
            try:
                work()
                if on_success:
                    self.after(0, on_success)
            except Exception as exc:
                if on_error:
                    self.after(0, lambda: on_error(exc))
                else:
                    self.after(0, lambda: self._show_error(str(exc)))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=runner, daemon=True).start()

    def _show_error(self, message: str) -> None:
        messagebox.showerror("Reliquary", message, parent=self)

    def _show_info(self, message: str) -> None:
        messagebox.showinfo("Reliquary", message, parent=self)

    def _show_create_vault(self) -> None:
        self._clear_container()
        frame = ctk.CTkFrame(self._container)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            frame,
            text="Create Vault",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=(24, 8))
        ctk.CTkLabel(
            frame,
            text="Set a master password to encrypt your secrets at rest.",
            text_color="gray70",
        ).pack(pady=(0, 24))

        password_entry = ctk.CTkEntry(
            frame,
            placeholder_text="Master password",
            show="*",
            width=320,
        )
        password_entry.pack(pady=8)

        confirm_entry = ctk.CTkEntry(
            frame,
            placeholder_text="Confirm master password",
            show="*",
            width=320,
        )
        confirm_entry.pack(pady=8)

        status_label = ctk.CTkLabel(frame, text="", text_color="#f87171")
        status_label.pack(pady=(8, 0))

        def submit() -> None:
            password = password_entry.get()
            confirm = confirm_entry.get()
            if password != confirm:
                status_label.configure(text="Passwords do not match.")
                return
            if not password:
                status_label.configure(text="Master password cannot be empty.")
                return

            status_label.configure(text="Creating vault…", text_color="gray70")

            def work() -> None:
                self.vault.create_vault(password)

            def on_success() -> None:
                password_entry.delete(0, tk.END)
                confirm_entry.delete(0, tk.END)
                self._show_main()

            def on_error(exc: Exception) -> None:
                status_label.configure(text=str(exc), text_color="#f87171")

            self._run_async(work, on_success, on_error)

        ctk.CTkButton(frame, text="Create Vault", command=submit, width=200).pack(
            pady=24
        )

    def _show_login(self) -> None:
        self._clear_container()
        frame = ctk.CTkFrame(self._container)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            frame,
            text="Unlock Vault",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=(24, 8))
        ctk.CTkLabel(
            frame,
            text="Enter your master password to access secrets.",
            text_color="gray70",
        ).pack(pady=(0, 24))

        password_entry = ctk.CTkEntry(
            frame,
            placeholder_text="Master password",
            show="*",
            width=320,
        )
        password_entry.pack(pady=8)
        password_entry.bind("<Return>", lambda _event: submit())

        status_label = ctk.CTkLabel(frame, text="", text_color="#f87171")
        status_label.pack(pady=(8, 0))

        def submit() -> None:
            password = password_entry.get()
            if not password:
                status_label.configure(text="Master password cannot be empty.")
                return

            status_label.configure(text="Unlocking…", text_color="gray70")

            def work() -> None:
                self.vault.unlock(password)

            def on_success() -> None:
                password_entry.delete(0, tk.END)
                self._show_main()

            def on_error(exc: Exception) -> None:
                if isinstance(exc, InvalidMasterPasswordError):
                    status_label.configure(
                        text="Invalid master password.",
                        text_color="#f87171",
                    )
                else:
                    status_label.configure(text=str(exc), text_color="#f87171")

            self._run_async(work, on_success, on_error)

        ctk.CTkButton(frame, text="Unlock", command=submit, width=200).pack(pady=24)

    def _show_main(self) -> None:
        self._clear_container()
        self._selected_path = None

        header = ctk.CTkFrame(self._container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header,
            text="Reliquary",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="Lock",
            width=90,
            command=self._lock_vault,
        ).pack(side="right")

        body = ctk.CTkFrame(self._container)
        body.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(body, width=260)
        sidebar.pack(side="left", fill="y", padx=(12, 6), pady=12)
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="Secrets",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(12, 8))

        self._paths_frame = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self._paths_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        ctk.CTkButton(
            sidebar,
            text="+ New Secret",
            command=self._show_new_secret_form,
        ).pack(fill="x", padx=12, pady=12)

        self._main_panel = ctk.CTkFrame(body)
        self._main_panel.pack(side="right", fill="both", expand=True, padx=(6, 12), pady=12)

        self._render_paths()
        self._show_welcome_panel()

    def _lock_vault(self) -> None:
        self.vault.lock()
        self._show_login()

    def _render_paths(self) -> None:
        for child in self._paths_frame.winfo_children():
            child.destroy()

        try:
            paths = self.vault.list_paths()
        except VaultLockedError:
            self._show_login()
            return

        if not paths:
            ctk.CTkLabel(
                self._paths_frame,
                text="No secrets yet.",
                text_color="gray60",
            ).pack(anchor="w", padx=4, pady=4)
            return

        for path in paths:
            is_selected = path == self._selected_path
            button = ctk.CTkButton(
                self._paths_frame,
                text=path,
                anchor="w",
                fg_color=("gray30", "gray25") if is_selected else "transparent",
                hover_color=("gray35", "gray30"),
                command=lambda p=path: self._select_path(p),
            )
            button.pack(fill="x", pady=2)

    def _clear_main_panel(self) -> None:
        for child in self._main_panel.winfo_children():
            child.destroy()

    def _show_welcome_panel(self) -> None:
        self._clear_main_panel()
        ctk.CTkLabel(
            self._main_panel,
            text="Select a secret from the sidebar or create a new one.",
            text_color="gray70",
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _select_path(self, path: str) -> None:
        self._selected_path = path
        self._render_paths()
        self._show_secret_detail(path)

    def _show_secret_detail(self, path: str) -> None:
        self._clear_main_panel()

        ctk.CTkLabel(
            self._main_panel,
            text=path,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 12))

        secret_box = ctk.CTkTextbox(self._main_panel, height=180)
        secret_box.pack(fill="both", expand=True, padx=20, pady=8)
        secret_box.configure(state="disabled")

        status_label = ctk.CTkLabel(self._main_panel, text="Decrypting…", text_color="gray70")
        status_label.pack(anchor="w", padx=20)

        def work() -> None:
            plaintext = self.vault.get_secret(path)

            def show() -> None:
                secret_box.configure(state="normal")
                secret_box.delete("1.0", tk.END)
                secret_box.insert("1.0", plaintext)
                secret_box.configure(state="disabled")
                status_label.configure(text="")

            self.after(0, show)

        def on_error(exc: Exception) -> None:
            status_label.configure(text=str(exc), text_color="#f87171")

        self._run_async(work, on_error=on_error)

        actions = ctk.CTkFrame(self._main_panel, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=16)

        ctk.CTkButton(
            actions,
            text="Edit",
            command=lambda: self._show_edit_secret_form(path),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions,
            text="Delete",
            fg_color="#b91c1c",
            hover_color="#991b1b",
            command=lambda: self._confirm_delete(path),
        ).pack(side="left")

    def _show_new_secret_form(self) -> None:
        self._selected_path = None
        self._render_paths()
        self._clear_main_panel()

        ctk.CTkLabel(
            self._main_panel,
            text="New Secret",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 12))

        path_entry = ctk.CTkEntry(
            self._main_panel,
            placeholder_text="Path (e.g. dev/aws_key)",
            width=400,
        )
        path_entry.pack(anchor="w", padx=20, pady=8)

        secret_box = ctk.CTkTextbox(self._main_panel, height=180)
        secret_box.pack(fill="both", expand=True, padx=20, pady=8)

        status_label = ctk.CTkLabel(self._main_panel, text="", text_color="#f87171")
        status_label.pack(anchor="w", padx=20)

        def save() -> None:
            path = path_entry.get().strip()
            plaintext = secret_box.get("1.0", tk.END).strip()
            if not path:
                status_label.configure(text="Path cannot be empty.")
                return

            status_label.configure(text="Saving…", text_color="gray70")

            def work() -> None:
                self.vault.add_secret(path, plaintext)

            def on_success() -> None:
                self._select_path(path)

            def on_error(exc: Exception) -> None:
                if isinstance(exc, SecretAlreadyExistsError):
                    status_label.configure(
                        text=f"Secret already exists: {path}",
                        text_color="#f87171",
                    )
                else:
                    status_label.configure(text=str(exc), text_color="#f87171")

            self._run_async(work, on_success, on_error)

        ctk.CTkButton(self._main_panel, text="Save Secret", command=save).pack(
            anchor="w", padx=20, pady=16
        )

    def _show_edit_secret_form(self, path: str) -> None:
        self._clear_main_panel()

        ctk.CTkLabel(
            self._main_panel,
            text=f"Edit: {path}",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(20, 12))

        secret_box = ctk.CTkTextbox(self._main_panel, height=220)
        secret_box.pack(fill="both", expand=True, padx=20, pady=8)

        status_label = ctk.CTkLabel(self._main_panel, text="Loading…", text_color="gray70")
        status_label.pack(anchor="w", padx=20)

        def work() -> None:
            plaintext = self.vault.get_secret(path)

            def populate() -> None:
                secret_box.insert("1.0", plaintext)
                status_label.configure(text="")

            self.after(0, populate)

        def on_error(exc: Exception) -> None:
            status_label.configure(text=str(exc), text_color="#f87171")

        self._run_async(work, on_error=on_error)

        def save() -> None:
            plaintext = secret_box.get("1.0", tk.END).strip()
            status_label.configure(text="Saving…", text_color="gray70")

            def work_save() -> None:
                self.vault.update_secret(path, plaintext)

            def on_success() -> None:
                self._select_path(path)

            def on_error_save(exc: Exception) -> None:
                status_label.configure(text=str(exc), text_color="#f87171")

            self._run_async(work_save, on_success, on_error_save)

        ctk.CTkButton(self._main_panel, text="Save Changes", command=save).pack(
            anchor="w", padx=20, pady=16
        )

    def _confirm_delete(self, path: str) -> None:
        if not messagebox.askyesno(
            "Delete Secret",
            f"Delete secret '{path}'? This cannot be undone.",
            parent=self,
        ):
            return

        def work() -> None:
            self.vault.delete_secret(path)

        def on_success() -> None:
            self._selected_path = None
            self._render_paths()
            self._show_welcome_panel()

        def on_error(exc: Exception) -> None:
            if isinstance(exc, SecretNotFoundError):
                self._show_error(str(exc))
                self._render_paths()
                self._show_welcome_panel()
            else:
                self._show_error(str(exc))

        self._run_async(work, on_success, on_error)


def main() -> None:
    app = ReliquaryApp()
    app.mainloop()


if __name__ == "__main__":
    main()
