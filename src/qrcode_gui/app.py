"""QR generator and webcam/image scanner using Tkinter."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .camera import RESOLUTIONS, choices, open_camera
from .decoder import decode_qr
from .qr import create_qr_image

try:
    import cv2
except ImportError:
    cv2 = None


class QRCodeApp:
    def __init__(self, root):
        self.root = root
        root.title("QR Code Studio")
        root.geometry("1240x820")
        root.minsize(900, 630)
        self.install_style()
        self.generated_image = None
        self.generated_preview = None
        self.camera_image = None
        self.cap = None
        self.camera_running = False
        self.camera_after_id = None
        self.failed_reads = 0
        self.reconnect_attempts = 0
        self.last_scanned = None
        self.decode_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qr-scan")
        self.decode_future = None
        self.decode_session = -1
        self.session_id = 0
        self.last_decode_at = 0.0
        self.image_future = None
        self.closing = False
        self.stop_after_scan = tk.BooleanVar(value=True)
        self.selected_camera = tk.StringVar(value="Automatic")
        self.selected_resolution = tk.StringVar(value="Full HD 1920x1080")
        self.build_ui()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def install_style(self):
        self.root.configure(bg="#eef3f9")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("DejaVu Sans", 10))
        style.configure("App.TFrame", background="#eef3f9")
        style.configure("Header.TLabel", background="#eef3f9", foreground="#0f172a",
                        font=("DejaVu Sans", 21, "bold"))
        style.configure("Caption.TLabel", background="#eef3f9", foreground="#64748b")
        style.configure("Card.TLabelframe", background="#ffffff", bordercolor="#dbe4ef",
                        relief="solid", borderwidth=1)
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#0f172a",
                        font=("DejaVu Sans", 12, "bold"))
        style.configure("TLabel", background="#ffffff", foreground="#334155")
        style.configure("TFrame", background="#ffffff")
        style.configure("TCheckbutton", background="#ffffff", foreground="#334155")
        style.configure("TButton", padding=(10, 7), relief="flat", background="#e7edf5",
                        foreground="#1e293b")
        style.map("TButton", background=[("active", "#dbe7f4")])
        style.configure("Accent.TButton", background="#2563eb", foreground="#ffffff",
                        font=("DejaVu Sans", 10, "bold"), padding=(12, 8))
        style.map("Accent.TButton", background=[("active", "#1d4ed8")],
                  foreground=[("active", "#ffffff")])
        style.configure("TCombobox", padding=5)
        style.configure("TScrollbar", background="#cbd5e1", troughcolor="#f1f5f9",
                        arrowcolor="#475569")
        self.text_options = dict(
            bg="#fbfdff", fg="#172033", insertbackground="#172033",
            selectbackground="#bfdbfe", font=("DejaVu Sans Mono", 10),
            relief="solid", bd=1, highlightthickness=1,
            highlightbackground="#dae3ee", highlightcolor="#2563eb",
            padx=9, pady=8,
        )

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer = ttk.Frame(self.root, padding=16, style="App.TFrame")
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1, uniform="pane")
        outer.columnconfigure(1, weight=1, uniform="pane")
        outer.rowconfigure(1, weight=1)

        header = ttk.Frame(outer, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        ttk.Label(header, text="▦  QR Code Studio", style="Header.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            header, text="Create • Save • Scan   |   Local, private and offline",
            style="Caption.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        left = ttk.LabelFrame(outer, text="Generate QR", padding=14,
                              style="Card.TLabelframe")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 7))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)
        ttk.Label(left, text="Text / URL").grid(row=0, column=0, sticky="w")
        input_box = ttk.Frame(left)
        input_box.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        input_box.columnconfigure(0, weight=1)
        self.text = tk.Text(
            input_box, height=8, wrap="word", undo=True, **self.text_options
        )
        self.text.grid(row=0, column=0, sticky="ew")
        input_scroll = ttk.Scrollbar(input_box, orient="vertical",
                                     command=self.text.yview)
        input_scroll.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=input_scroll.set)
        row = ttk.Frame(left)
        row.grid(row=2, column=0, sticky="ew", pady=9)
        ttk.Button(row, text="Generate QR", command=self.generate,
                   style="Accent.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Save PNG", command=self.save_png).pack(side="left", padx=6)
        ttk.Button(row, text="Clear", command=self.clear_generator).pack(side="left", padx=6)
        self.qr_label = ttk.Label(
            left, text="Generated QR code will appear here", anchor="center"
        )
        self.qr_label.grid(row=3, column=0, sticky="nsew")
        self.status = ttk.Label(left, text="Ctrl+Enter to generate", anchor="w")
        self.status.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.text.bind("<Control-Return>", self.generate)
        self.text.focus_set()

        right = ttk.LabelFrame(outer, text="Scan QR", padding=14,
                               style="Card.TLabelframe")
        right.grid(row=1, column=1, sticky="nsew", padx=(7, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(4, weight=1)
        ttk.Label(right, text="Scanned result").grid(row=0, column=0, sticky="w")
        result_frame = ttk.Frame(right)
        result_frame.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        result_frame.columnconfigure(0, weight=1)
        self.scan_result = tk.Text(
            result_frame, height=8, wrap="word", **self.text_options
        )
        self.scan_result.grid(row=0, column=0, sticky="ew")
        scroll = ttk.Scrollbar(result_frame, orient="vertical",
                               command=self.scan_result.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.scan_result.configure(yscrollcommand=scroll.set)

        row = ttk.Frame(right)
        row.grid(row=2, column=0, sticky="ew", pady=8)
        ttk.Button(row, text="Copy Result", command=self.copy_scan_result).pack(
            side="left", padx=(0, 5)
        )
        ttk.Button(row, text="Use as Input", command=self.use_scan_result).pack(
            side="left", padx=5
        )
        ttk.Button(row, text="Scan Image", command=self.scan_image).pack(
            side="left", padx=5
        )
        ttk.Button(row, text="Clear", command=self.clear_scan_result).pack(
            side="left", padx=5
        )

        row = ttk.Frame(right)
        row.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.camera_button = ttk.Button(
            row, text="Start Camera", command=self.toggle_camera,
            style="Accent.TButton",
        )
        self.camera_button.pack(side="left", padx=(0, 6))
        self.camera_selector = ttk.Combobox(
            row, textvariable=self.selected_camera, values=choices(),
            state="readonly", width=16
        )
        self.camera_selector.pack(side="left", padx=4)
        ttk.Button(row, text="↻", width=3, command=self.refresh_cameras).pack(
            side="left", padx=4
        )

        # Resolution changes take effect when starting/restarting the camera.
        options_row = ttk.Frame(right)
        options_row.grid(row=6, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(options_row, text="Capture quality:").pack(side="left", padx=(0, 5))
        ttk.Combobox(
            options_row, textvariable=self.selected_resolution,
            values=list(RESOLUTIONS), state="readonly", width=20,
        ).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(
            options_row, text="Stop after scan", variable=self.stop_after_scan
        ).pack(side="left")

        self.camera_label = ttk.Label(
            right, text="Press Start Camera or Scan Image", anchor="center"
        )
        self.camera_label.grid(row=4, column=0, sticky="nsew")
        self.camera_status = ttk.Label(
            right, text="Camera is off", anchor="w", wraplength=480
        )
        self.camera_status.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(
            right,
            text="For dense codes, use Full HD, fill more of the frame and avoid glare.",
            foreground="#64748b", wraplength=490,
        ).grid(row=7, column=0, sticky="ew", pady=(5, 0))

    def generate(self, event=None):
        content = self.text.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("No content", "Enter text or a URL.")
            return "break"
        try:
            self.generated_image = create_qr_image(content)
            preview = self.generated_image.copy()
            preview.thumbnail((500, 500))
            self.generated_preview = ImageTk.PhotoImage(preview)
            self.qr_label.configure(image=self.generated_preview, text="")
            self.status.configure(text=f"Generated QR — {len(content)} characters")
        except Exception as exc:
            messagebox.showerror("QR generation failed", str(exc))
        return "break"

    def save_png(self):
        if self.generated_image is None:
            self.generate()
        if self.generated_image is None:
            return
        path = filedialog.asksaveasfilename(
            title="Save QR code", defaultextension=".png",
            filetypes=[("PNG image", "*.png")], initialfile="qrcode.png",
        )
        if path:
            try:
                self.generated_image.save(path, format="PNG")
                self.status.configure(text=f"Saved PNG: {path}")
            except OSError as exc:
                messagebox.showerror("Unable to save", str(exc))

    def clear_generator(self):
        self.text.delete("1.0", "end")
        self.generated_image = None
        self.generated_preview = None
        self.qr_label.configure(image="", text="Generated QR code will appear here")
        self.status.configure(text="Ctrl+Enter to generate")
        self.text.focus_set()

    def refresh_cameras(self):
        current = self.selected_camera.get()
        options = choices()
        self.camera_selector.configure(values=options)
        self.selected_camera.set(current if current in options else "Automatic")

    def toggle_camera(self):
        if self.camera_running:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self, retry=False):
        if self.camera_running:
            return
        if not retry:
            self.reconnect_attempts = 0
            self.last_scanned = None
        if cv2 is None:
            self.camera_status.configure(text="OpenCV is not installed.")
            messagebox.showerror("Missing dependency", "Install the project dependencies.")
            return
        self.camera_status.configure(text="Opening camera…")
        self.root.update_idletasks()
        cap, device, error = open_camera(
            cv2, self.selected_camera.get(), self.selected_resolution.get()
        )
        if cap is None:
            self.camera_status.configure(text=error)
            self.camera_button.configure(text="Start Camera")
            return
        self.cap = cap
        self.session_id += 1
        self.decode_future = None
        self.last_decode_at = 0
        self.failed_reads = 0
        self.camera_running = True
        self.camera_button.configure(text="Stop Camera")
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.camera_status.configure(
            text=f"Camera {device} • {w}×{h} • scanning full-resolution frames"
        )
        self.update_camera()

    def stop_camera(self, message="Camera stopped.", clear_preview=False):
        self.camera_running = False
        self.session_id += 1
        self.decode_future = None
        if self.camera_after_id is not None:
            try:
                self.root.after_cancel(self.camera_after_id)
            except tk.TclError:
                pass
            self.camera_after_id = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.camera_button.configure(text="Start Camera")
        self.camera_status.configure(text=message)
        if clear_preview:
            self.camera_image = None
            self.camera_label.configure(image="", text="Camera is off")

    def update_camera(self):
        if not self.camera_running or self.cap is None:
            return
        self.camera_after_id = None
        try:
            ok, frame = self.cap.read()
        except Exception:
            ok, frame = False, None
        if not ok or frame is None or not getattr(frame, "size", 0):
            self.failed_reads += 1
            if self.failed_reads >= 10:
                self.reconnect_attempts += 1
                attempt = self.reconnect_attempts
                self.stop_camera(message=f"Lost camera frames. Reconnecting ({attempt}/3)…")
                if attempt <= 3:
                    self.camera_after_id = self.root.after(
                        650, lambda: self.start_camera(retry=True)
                    )
                else:
                    self.camera_status.configure(
                        text="Camera failed repeatedly. Check other apps, select a "
                             "different device, or connect the Snap camera permission."
                    )
                return
            self.camera_status.configure(text="Waiting for webcam frame…")
            self.camera_after_id = self.root.after(100, self.update_camera)
            return

        self.failed_reads = 0
        # Only the small preview is resized. QR decoding uses the unscaled
        # original frame, on a worker thread so the UI stays responsive.
        self.show_camera_frame(frame)
        if self.check_decode_result():
            return
        now = time.monotonic()
        if self.decode_future is None and now - self.last_decode_at >= 0.22:
            self.decode_session = self.session_id
            self.last_decode_at = now
            self.decode_future = self.decode_pool.submit(decode_qr, frame.copy())
        if self.camera_running:
            self.camera_after_id = self.root.after(50, self.update_camera)

    def check_decode_result(self):
        future = self.decode_future
        if future is None or not future.done():
            return False
        self.decode_future = None
        try:
            text = future.result()
        except Exception as exc:
            self.camera_status.configure(text=f"Scanner error: {exc}")
            return False
        if not self.camera_running or self.decode_session != self.session_id:
            return False
        if text and text != self.last_scanned:
            self.accept_scan(text)
            if self.stop_after_scan.get():
                self.stop_camera(message="QR decoded successfully.")
                return True
        return False

    def show_camera_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail((560, 410))
        self.camera_image = ImageTk.PhotoImage(image)
        self.camera_label.configure(image=self.camera_image, text="")

    def accept_scan(self, value):
        if not value or value == self.last_scanned:
            return
        self.last_scanned = value
        self.scan_result.delete("1.0", "end")
        self.scan_result.insert("1.0", value)
        self.camera_status.configure(text="QR code decoded successfully.")
        self.root.bell()

    def scan_image(self):
        if cv2 is None:
            messagebox.showerror("Missing dependency", "OpenCV is required to decode QR codes.")
            return
        filename = filedialog.askopenfilename(
            title="Open QR image", filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*")
            ]
        )
        if not filename:
            return
        try:
            frame = cv2.imread(filename)
            if frame is None:
                raise ValueError("This file is not a supported image.")
            self.camera_status.configure(text="Decoding selected image…")
            self.image_future = self.decode_pool.submit(decode_qr, frame)
            self.root.after(90, lambda: self.poll_image_decode(filename, self.image_future))
        except (OSError, ValueError, cv2.error) as exc:
            messagebox.showerror("Cannot read image", str(exc))

    def poll_image_decode(self, filename, future):
        if self.closing or future is not self.image_future:
            return
        if not future.done():
            self.root.after(90, lambda: self.poll_image_decode(filename, future))
            return
        self.image_future = None
        try:
            decoded = future.result()
        except Exception as exc:
            messagebox.showerror("Cannot decode image", str(exc))
            return
        if not decoded:
            messagebox.showinfo("QR not found", "No readable QR code was found.")
            return
        self.last_scanned = None
        self.accept_scan(decoded)
        self.camera_status.configure(text=f"Decoded QR from {os.path.basename(filename)}")

    def get_scan_result(self):
        return self.scan_result.get("1.0", "end-1c").strip()

    def clear_scan_result(self):
        self.scan_result.delete("1.0", "end")
        self.last_scanned = None

    def copy_scan_result(self):
        value = self.get_scan_result()
        if value:
            self.root.clipboard_clear()
            self.root.clipboard_append(value)
            self.camera_status.configure(text="Result copied to clipboard.")

    def use_scan_result(self):
        value = self.get_scan_result()
        if value:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", value)
            self.text.focus_set()
            self.status.configure(text="Scanner result copied to input.")

    def on_close(self):
        self.closing = True
        self.stop_camera()
        self.decode_pool.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()


def main():
    root = tk.Tk()
    QRCodeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
