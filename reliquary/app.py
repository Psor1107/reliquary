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
from reliquary.database import SQLiteStorage

# Configuração Base do Tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class ReliquaryApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Reliquary Vault")
        self.geometry("1024x640")
        self.minsize(800, 500)

        storage = SQLiteStorage()
        self.vault = Vault(storage=storage)
        self._selected_path: str | None = None
        self._busy = False
        self._current_master_password: str | None = None

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True, padx=20, pady=20)

        if self.vault.is_initialized():
            self._show_login()
        else:
            self._show_create_vault()

    def _clear_container(self) -> None:
        for child in self._container.winfo_children():
            child.destroy()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.config(cursor="watch" if busy else "")

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
                # FIX: Binding 'exc' to 'e' prevents NameError closure bugs 
                # caused by Python 3 exception garbage collection.
                if on_error:
                    self.after(0, lambda e=exc: on_error(e))
                else:
                    self.after(0, lambda e=exc: self._show_error(str(e) or "An unknown error occurred."))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=runner, daemon=True).start()

    def _show_error(self, message: str) -> None:
        messagebox.showerror("Reliquary Error", message, parent=self)

    # ==========================================
    # TELA 1: CRIAÇÃO DO COFRE
    # ==========================================
    def _show_create_vault(self) -> None:
        self._clear_container()
        frame = ctk.CTkFrame(self._container, corner_radius=15)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            frame,
            text="🛡️ Initialize Vault",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(pady=(30, 8), padx=40)
        
        ctk.CTkLabel(
            frame,
            text="Set a master password to encrypt your secrets at rest.\nIf you lose this, your data is gone forever.",
            text_color="gray60",
            justify="center"
        ).pack(pady=(0, 24), padx=40)

        password_entry = ctk.CTkEntry(frame, placeholder_text="Master password", show="•", width=320, height=40)
        password_entry.pack(pady=8)

        confirm_entry = ctk.CTkEntry(frame, placeholder_text="Confirm master password", show="•", width=320, height=40)
        confirm_entry.pack(pady=8)

        status_label = ctk.CTkLabel(frame, text="", text_color="#ef4444", font=ctk.CTkFont(size=13))
        status_label.pack(pady=(8, 0))

        def submit() -> None:
            password = password_entry.get()
            confirm = confirm_entry.get()
            
            if not password:
                status_label.configure(text="⚠️ Master password cannot be empty.")
                return
            if password != confirm:
                status_label.configure(text="⚠️ Passwords do not match.")
                confirm_entry.delete(0, tk.END)
                return

            status_label.configure(text="⏳ Forging vault cryptographically...", text_color="#10b981")
            
            def work() -> None:
                self.vault.create_vault(password)

            def on_success() -> None:
                self._current_master_password = password
                self._show_main()

            def on_error(exc: Exception) -> None:
                status_label.configure(text=f"⚠️ {str(exc) or 'Failed to create vault.'}", text_color="#ef4444")

            self._run_async(work, on_success, on_error)

        ctk.CTkButton(frame, text="Create Vault", command=submit, width=200, height=40, font=ctk.CTkFont(weight="bold")).pack(pady=(16, 30))

    # ==========================================
    # TELA 2: LOGIN (DESBLOQUEIO)
    # ==========================================
    def _show_login(self) -> None:
        self._clear_container()
        frame = ctk.CTkFrame(self._container, corner_radius=15)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            frame,
            text="🔒 Unlock Reliquary",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(pady=(30, 8), padx=40)
        
        ctk.CTkLabel(
            frame,
            text="Enter your master password to decrypt the local registry.",
            text_color="gray60",
        ).pack(pady=(0, 24), padx=40)

        # FIX: Container rígido para o "olhinho" não empurrar a tela
        entry_frame = ctk.CTkFrame(frame, fg_color="transparent", width=360, height=40)
        entry_frame.pack_propagate(False)
        entry_frame.pack(pady=8)

        password_entry = ctk.CTkEntry(entry_frame, placeholder_text="Master password", show="•", width=310, height=40)
        password_entry.pack(side="left", padx=(0, 8))
        
        def toggle_password() -> None:
            current_show = password_entry.cget("show")
            if current_show == "•":
                password_entry.configure(show="")
                toggle_btn.configure(text="🙈")
            else:
                password_entry.configure(show="•")
                toggle_btn.configure(text="👁️")
            password_entry.focus()

        toggle_btn = ctk.CTkButton(entry_frame, text="👁️", width=40, height=40, fg_color="transparent", hover_color="gray30", command=toggle_password)
        toggle_btn.pack(side="right")

        password_entry.bind("<Return>", lambda _event: submit())

        status_label = ctk.CTkLabel(frame, text="", text_color="#ef4444", font=ctk.CTkFont(size=13))
        status_label.pack(pady=(8, 0))

        def submit() -> None:
            password = password_entry.get()
            if not password:
                status_label.configure(text="⚠️ Please enter your password.")
                return

            status_label.configure(text="⏳ Decrypting...", text_color="#10b981")
            password_entry.configure(state="disabled")

            def work() -> None:
                self.vault.unlock(password)

            def on_success() -> None:
                self._current_master_password = password
                self._show_main()

            def on_error(exc: Exception) -> None:
                password_entry.configure(state="normal")
                password_entry.delete(0, tk.END)
                
                error_msg = str(exc)
                if not error_msg or isinstance(exc, InvalidMasterPasswordError) or "InvalidToken" in str(type(exc)):
                    error_msg = "Invalid master password."
                    
                status_label.configure(text=f"⚠️ {error_msg}", text_color="#ef4444")

            self._run_async(work, on_success, on_error)

        ctk.CTkButton(frame, text="Unlock", command=submit, width=200, height=40, font=ctk.CTkFont(weight="bold")).pack(pady=(16, 30))

    # ==========================================
    # TELA 3: PAINEL PRINCIPAL
    # ==========================================
    def _show_main(self) -> None:
        self._clear_container()
        self._selected_path = None

        header = ctk.CTkFrame(self._container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header,
            text="🛡️ Reliquary Vault",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="🔒 Lock Vault",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color="gray80",
            hover_color="gray30",
            command=self._lock_vault,
        ).pack(side="right")

        body = ctk.CTkFrame(self._container)
        body.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(body, width=260, corner_radius=0)
        sidebar.pack(side="left", fill="y", padx=0, pady=0)
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="Secret Keys",
            text_color="gray60",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 8))

        self._paths_frame = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self._paths_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        ctk.CTkButton(
            sidebar,
            text="➕ New Secret",
            font=ctk.CTkFont(weight="bold"),
            command=self._show_new_secret_form,
        ).pack(fill="x", padx=16, pady=16)

        self._main_panel = ctk.CTkFrame(body, fg_color="transparent")
        self._main_panel.pack(side="right", fill="both", expand=True, padx=16, pady=16)

        self._render_paths()
        self._show_welcome_panel()

    def _lock_vault(self) -> None:
        self.vault.lock()
        self._current_master_password = None
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
                text="No secrets registered.",
                text_color="gray50",
                font=ctk.CTkFont(size=13, slant="italic")
            ).pack(anchor="w", padx=8, pady=8)
            return

        for path in sorted(paths):
            is_selected = path == self._selected_path
            button = ctk.CTkButton(
                self._paths_frame,
                text=f"🔑 {path}",
                anchor="w",
                fg_color=("#10b981", "#059669") if is_selected else "transparent",
                text_color="white" if is_selected else "gray80",
                hover_color=("#34d399", "#10b981") if is_selected else "gray30",
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
            text="Select a secret from the sidebar\nor forge a new one.",
            text_color="gray50",
            font=ctk.CTkFont(size=16),
            justify="center"
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _select_path(self, path: str, force_refresh_content: str | None = None) -> None:
        self._selected_path = path
        self._render_paths()
        self._show_secret_detail(path, force_refresh_content)

    # ==========================================
    # VISUALIZAR SEGREDO
    # ==========================================
    def _show_secret_detail(self, path: str, forced_plaintext: str | None = None) -> None:
        self._clear_main_panel()

        header_frame = ctk.CTkFrame(self._main_panel, fg_color="transparent")
        header_frame.pack(fill="x", anchor="w", pady=(10, 16))
        
        ctk.CTkLabel(
            header_frame,
            text="Secret Details",
            text_color="gray60",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame,
            text=path,
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", pady=(4, 0))

        secret_box = ctk.CTkTextbox(self._main_panel, height=200, font=ctk.CTkFont(family="Consolas", size=14))
        secret_box.pack(fill="both", expand=True, pady=8)
        
        status_label = ctk.CTkLabel(self._main_panel, text="⏳ Decrypting payload...", text_color="#10b981")
        status_label.pack(anchor="w", pady=(4, 8))

        if forced_plaintext is not None:
            secret_box.insert("1.0", forced_plaintext)
            secret_box.configure(state="disabled")
            status_label.destroy()
        else:
            secret_box.configure(state="disabled")
            def work() -> None:
                plaintext = self.vault.get_secret(path)
                def show() -> None:
                    secret_box.configure(state="normal")
                    secret_box.delete("1.0", tk.END)
                    secret_box.insert("1.0", plaintext)
                    secret_box.configure(state="disabled")
                    status_label.destroy()
                self.after(0, show)
            def on_error(exc: Exception) -> None:
                status_label.configure(text=f"⚠️ Error: {str(exc)}", text_color="#ef4444")

            self._run_async(work, on_error=on_error)

        actions = ctk.CTkFrame(self._main_panel, fg_color="transparent")
        actions.pack(fill="x", pady=16)

        ctk.CTkButton(
            actions,
            text="✏️ Edit",
            width=120,
            command=lambda: self._show_edit_secret_form(path),
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            actions,
            text="🗑️ Delete",
            width=120,
            fg_color="transparent",
            border_width=1,
            border_color="#ef4444",
            text_color="#ef4444",
            hover_color="#7f1d1d",
            command=lambda: self._confirm_delete(path),
        ).pack(side="left")

    # ==========================================
    # CRIAR NOVO SEGREDO
    # ==========================================
    def _show_new_secret_form(self) -> None:
        self._selected_path = None
        self._render_paths()
        self._clear_main_panel()

        ctk.CTkLabel(
            self._main_panel,
            text="Forge New Secret",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", pady=(10, 16))

        ctk.CTkLabel(self._main_panel, text="Registry Path (e.g. prod/db_password)", text_color="gray60", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        path_entry = ctk.CTkEntry(self._main_panel, placeholder_text="Enter path identifier", width=400, height=40)
        path_entry.pack(anchor="w", pady=(4, 16))

        ctk.CTkLabel(self._main_panel, text="Secret Payload", text_color="gray60", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        secret_box = ctk.CTkTextbox(self._main_panel, height=200, font=ctk.CTkFont(family="Consolas", size=14))
        secret_box.pack(fill="both", expand=True, pady=(4, 8))

        status_label = ctk.CTkLabel(self._main_panel, text="", text_color="#ef4444")
        status_label.pack(anchor="w")

        def save() -> None:
            path = path_entry.get().strip()
            plaintext = secret_box.get("1.0", tk.END).strip()
            
            if not path:
                status_label.configure(text="⚠️ Path identifier cannot be empty.")
                return
            if not plaintext:
                status_label.configure(text="⚠️ Secret payload cannot be empty.")
                return

            status_label.configure(text="⏳ Encrypting and saving...", text_color="#10b981")

            def work() -> None:
                self.vault.add_secret(path, plaintext)

            def on_success() -> None:
                # FIX: Injeta o texto forçado para evitar a condição de corrida de threads
                self._select_path(path, force_refresh_content=plaintext)

            def on_error(exc: Exception) -> None:
                if isinstance(exc, SecretAlreadyExistsError):
                    status_label.configure(text=f"⚠️ Secret already exists at: {path}", text_color="#ef4444")
                else:
                    status_label.configure(text=f"⚠️ Error: {str(exc)}", text_color="#ef4444")

            self._run_async(work, on_success, on_error)

        ctk.CTkButton(self._main_panel, text="Save to Vault", command=save, height=40, font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=16)

    # ==========================================
    # EDITAR SEGREDO
    # ==========================================
    def _show_edit_secret_form(self, path: str) -> None:
        self._clear_main_panel()

        header_frame = ctk.CTkFrame(self._main_panel, fg_color="transparent")
        header_frame.pack(fill="x", anchor="w", pady=(10, 16))
        
        ctk.CTkLabel(header_frame, text="Editing Payload For", text_color="gray60", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header_frame, text=path, font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(4, 0))

        secret_box = ctk.CTkTextbox(self._main_panel, height=240, font=ctk.CTkFont(family="Consolas", size=14))
        secret_box.pack(fill="both", expand=True, pady=8)

        status_label = ctk.CTkLabel(self._main_panel, text="⏳ Retrieving original payload...", text_color="#10b981")
        status_label.pack(anchor="w")

        def work() -> None:
            plaintext = self.vault.get_secret(path)
            def populate() -> None:
                secret_box.insert("1.0", plaintext)
                status_label.configure(text="")
            self.after(0, populate)

        def on_error(exc: Exception) -> None:
            status_label.configure(text=f"⚠️ Error: {str(exc)}", text_color="#ef4444")

        self._run_async(work, on_error=on_error)

        actions_frame = ctk.CTkFrame(self._main_panel, fg_color="transparent")
        actions_frame.pack(fill="x", pady=16)

        def save() -> None:
            new_plaintext = secret_box.get("1.0", tk.END).strip()
            status_label.configure(text="⏳ Committing changes...", text_color="#10b981")

            def work_save() -> None:
                self.vault.update_secret(path, new_plaintext)

            def on_success() -> None:
                self._select_path(path, force_refresh_content=new_plaintext)

            def on_error_save(exc: Exception) -> None:
                status_label.configure(text=f"⚠️ Error: {str(exc)}", text_color="#ef4444")

            self._run_async(work_save, on_success, on_error_save)

        ctk.CTkButton(actions_frame, text="💾 Commit Changes", command=save, height=40, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 12))
        ctk.CTkButton(actions_frame, text="Cancel", fg_color="transparent", border_width=1, hover_color="gray30", height=40, command=lambda: self._show_secret_detail(path)).pack(side="left")

    # ==========================================
    # DELETAR SEGREDO
    # ==========================================
    def _confirm_delete(self, path: str) -> None:
        if not messagebox.askyesno(
            "Obliterate Secret",
            f"Are you sure you want to permanently delete '{path}'?\n\nThis action cannot be reversed.",
            parent=self,
            icon="warning"
        ):
            return

        def work() -> None:
            self.vault.delete_secret(path)

        def on_success() -> None:
            self._selected_path = None
            self._render_paths()
            self._show_welcome_panel()

        def on_error(exc: Exception) -> None:
            self._show_error(str(exc))
            self._render_paths()
            self._show_welcome_panel()

        self._run_async(work, on_success, on_error)


def main() -> None:
    app = ReliquaryApp()
    app.mainloop()


if __name__ == "__main__":
    main()
