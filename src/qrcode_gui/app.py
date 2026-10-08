"""QR generator and webcam/image scanner using Tkinter."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .camera import choices, open_camera
from .qr import create_qr_image

try:
    import cv2
except ImportError:
    cv2 = None


class QRCodeApp:
    def __init__(self, root):
        self.root = root
        root.title("QR Code Generator & Scanner")
        root.geometry("1160x740")
        root.minsize(850, 600)
        self.generated_image = None
        self.generated_preview = None
        self.camera_image = None
        self.cap = None
        self.camera_running = False
        self.camera_after_id = None
        self.failed_reads = 0
        self.reconnect_attempts = 0
        self.last_scanned = None
        self.qr_detector = cv2.QRCodeDetector() if cv2 else None
        self.stop_after_scan = tk.BooleanVar(value=True)
        self.selected_camera = tk.StringVar(value="Automatic")
        self.build_ui()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer = ttk.Frame(self.root, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1, uniform="pane")
        outer.columnconfigure(1, weight=1, uniform="pane")
        outer.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(outer, text="QR Generator", padding=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)
        ttk.Label(left, text="Text / URL").grid(row=0, column=0, sticky="w")
        self.text = tk.Text(left, height=7, wrap="word", undo=True)
        self.text.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        row = ttk.Frame(left)
        row.grid(row=2, column=0, sticky="ew", pady=9)
        ttk.Button(row, text="Generate QR", command=self.generate).pack(side="left", padx=(0, 6))
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

        right = ttk.LabelFrame(outer, text="QR Scanner", padding=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(4, weight=1)
        ttk.Label(right, text="Scanned result").grid(row=0, column=0, sticky="w")
        result_frame = ttk.Frame(right)
        result_frame.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        result_frame.columnconfigure(0, weight=1)
        self.scan_result = tk.Text(result_frame, height=7, wrap="word")
        self.scan_result.grid(row=0, column=0, sticky="ew")
        scroll = ttk.Scrollbar(result_frame, command=self.scan_result.yview)
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
            row, text="Start Camera", command=self.toggle_camera
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
        ttk.Checkbutton(
            row, text="Stop after scan", variable=self.stop_after_scan
        ).pack(side="left", padx=4)

        self.camera_label = ttk.Label(
            right, text="Press Start Camera or Scan Image", anchor="center"
        )
        self.camera_label.grid(row=4, column=0, sticky="nsew")
        self.camera_status = ttk.Label(
            right, text="Camera is off", anchor="w", wraplength=480
        )
        self.camera_status.grid(row=5, column=0, sticky="ew", pady=(8, 0))

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
        cap, device, error = open_camera(cv2, self.selected_camera.get())
        if cap is None:
            self.camera_status.configure(text=error)
            self.camera_button.configure(text="Start Camera")
            return
        self.cap = cap
        self.failed_reads = 0
        self.camera_running = True
        self.camera_button.configure(text="Stop Camera")
        self.camera_status.configure(text=f"Camera active: {device} — point at a QR code")
        self.update_camera()

    def stop_camera(self, message="Camera stopped.", clear_preview=False):
        self.camera_running = False
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
        display = frame.copy()
        decoded = ""
        try:
            decoded, points, _ = self.qr_detector.detectAndDecode(frame)
            if points is not None:
                points = points.astype(int).reshape(-1, 2)
                for idx in range(len(points)):
                    cv2.line(
                        display, tuple(points[idx]),
                        tuple(points[(idx + 1) % len(points)]), (0, 255, 0), 3
                    )
        except cv2.error:
            pass
        self.show_camera_frame(display)
        if decoded:
            self.accept_scan(decoded)
            if self.stop_after_scan.get():
                self.stop_camera(message="QR code decoded successfully.")
                return
        if self.camera_running:
            self.camera_after_id = self.root.after(50, self.update_camera)

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
            decoded, _, _ = self.qr_detector.detectAndDecode(frame)
            if not decoded:
                messagebox.showinfo("QR not found", "No readable QR code was found.")
                return
            self.last_scanned = None
            self.accept_scan(decoded)
            self.camera_status.configure(text=f"Decoded QR from {os.path.basename(filename)}")
        except (OSError, ValueError, cv2.error) as exc:
            messagebox.showerror("Cannot read image", str(exc))

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
        self.stop_camera()
        self.root.destroy()


def main():
    root = tk.Tk()
    QRCodeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
