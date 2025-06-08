import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Canvas
from PIL import Image, ImageTk, ImageDraw
import configparser
import os
import csv
import shutil
import matplotlib.pyplot as plt
from tooltalk_api import TooltalkAPI

class DragLabel:
    def __init__(self, canvas, label, x, y):
        self.canvas = canvas
        self.label = label
        self.id = canvas.create_text(x, y, text=label, font=("Arial", 16, "bold"), fill="red", tags="draggable")
        self._drag_data = {"x": 0, "y": 0}
        canvas.tag_bind(self.id, "<ButtonPress-1>", self.on_start)
        canvas.tag_bind(self.id, "<ButtonRelease-1>", self.on_drop)
        canvas.tag_bind(self.id, "<B1-Motion>", self.on_drag)

    def on_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def on_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.canvas.move(self.id, dx, dy)
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def on_drop(self, event):
        pass

    def get_position(self):
        return self.canvas.coords(self.id)

class TorqueTestWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("Torque Test Tooltalk Wizard")
        self.api = TooltalkAPI()
        self.config = configparser.ConfigParser()
        self.config_file = 'config/settings.ini'
        self.load_config()
        self.state = {}
        self.frames = {}
        self.current_frame = None
        self.init_folders()
        self.show_step("connect")

    def load_config(self):
        if not os.path.exists(self.config_file):
            os.makedirs('config', exist_ok=True)
            self.config['DEFAULT'] = {
                'com_port': 'COM3',
                'default_target_torque': '24',
                'output_directory': 'results'
            }
            with open(self.config_file, 'w') as f:
                self.config.write(f)
        self.config.read(self.config_file)

    def init_folders(self):
        os.makedirs('lib', exist_ok=True)
        os.makedirs('results', exist_ok=True)

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = None

    def show_step(self, step):
        self.clear_frame()
        if step == "connect":
            self.show_connect()
        elif step == "hole_sample":
            self.show_hole_sample()
        elif step == "image_upload":
            self.show_image_upload()
        elif step == "label_placement":
            self.show_label_placement()
        elif step == "torque_setting":
            self.show_torque_setting()
        elif step == "run_test":
            self.show_run_test()
        elif step == "show_plot":
            self.show_plot()

    def show_connect(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Connect to Tooltalk Controller (MT6000)", font=("Arial", 16)).pack(pady=10)
        port_var = tk.StringVar(value=self.config['DEFAULT']['com_port'])
        port_entry = ttk.Entry(frame, textvariable=port_var, width=10)
        port_entry.pack(pady=5)
        status_lbl = ttk.Label(frame, text="Not connected", foreground="red")
        status_lbl.pack(pady=5)
        def connect():
            if self.api.connect(port_var.get()):
                status_lbl.config(text="Connected", foreground="green")
                self.state['com_port'] = port_var.get()
                self.root.after(800, lambda: self.show_step("hole_sample"))
            else:
                messagebox.showerror("Connection Failed", "Could not connect to controller.")
        ttk.Button(frame, text="Connect", command=connect).pack(pady=10)
        self.current_frame = frame

    def show_hole_sample(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Define Screw Holes and Samples", font=("Arial", 16)).pack(pady=10)
        holes_var = tk.IntVar(value=5)
        samples_var = tk.IntVar(value=1)
        ttk.Label(frame, text="Number of screw holes (A, B, ...):").pack()
        ttk.Entry(frame, textvariable=holes_var, width=5).pack(pady=2)
        ttk.Label(frame, text="Number of samples:").pack()
        ttk.Entry(frame, textvariable=samples_var, width=5).pack(pady=2)
        def next_():
            n = holes_var.get()
            s = samples_var.get()
            if n < 1 or s < 1 or n > 26:
                messagebox.showerror("Input Error", "Number of holes/samples must be 1-26.")
                return
            self.state['holes'] = [chr(65+i) for i in range(n)]
            self.state['samples'] = s
            self.show_step("image_upload")
        ttk.Button(frame, text="Next", command=next_).pack(pady=10)
        self.current_frame = frame

    def show_image_upload(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Upload Image(s) of Screw Hole Placement", font=("Arial", 16)).pack(pady=10)
        img_count_var = tk.IntVar(value=1)
        ttk.Label(frame, text="How many images?").pack()
        ttk.Entry(frame, textvariable=img_count_var, width=5).pack(pady=2)
        img_files = []
        img_hole_counts = []
        img_labels = ttk.Label(frame, text="No images uploaded yet.")
        img_labels.pack(pady=5)
        def upload_images():
            count = img_count_var.get()
            if count < 1 or count > len(self.state['holes']):
                messagebox.showerror("Input Error", "Image count must be 1 or more, and not more than number of holes.")
                return
            img_files.clear()
            img_hole_counts.clear()
            img_labels.config(text="")
            for i in range(count):
                file = filedialog.askopenfilename(title=f"Select image {i+1}", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
                if not file:
                    messagebox.showerror("Input Error", "All images must be selected.")
                    return
                img_files.append(file)
            total_holes = len(self.state['holes'])
            remaining = total_holes
            for i in range(count):
                if count == 1:
                    img_hole_counts.append(total_holes)
                else:
                    prompt = f"How many screw holes in image {i+1}? (Remaining: {remaining})"
                    n = tk.simpledialog.askinteger("Holes per image", prompt, minvalue=1, maxvalue=remaining)
                    if n is None or n > remaining:
                        messagebox.showerror("Input Error", "Invalid hole count.")
                        return
                    img_hole_counts.append(n)
                    remaining -= n
            if sum(img_hole_counts) != total_holes:
                messagebox.showerror("Input Error", "Total holes assigned does not match.")
                return
            # Copy images to lib/
            lib_files = []
            for i, f in enumerate(img_files):
                ext = os.path.splitext(f)[1]
                dest = os.path.join('lib', f"img_{i+1}{ext}")
                shutil.copy(f, dest)
                lib_files.append(dest)
            self.state['images'] = lib_files
            self.state['img_hole_counts'] = img_hole_counts
            img_labels.config(text="\n".join([os.path.basename(f) for f in lib_files]))
        ttk.Button(frame, text="Upload Images", command=upload_images).pack(pady=5)
        def next_():
            if 'images' not in self.state:
                messagebox.showerror("Input Error", "Please upload images and assign holes.")
                return
            self.show_step("label_placement")
        ttk.Button(frame, text="Next", command=next_).pack(pady=10)
        self.current_frame = frame

    def show_label_placement(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Drag and Drop Labels for Screw Holes", font=("Arial", 16)).pack(pady=10)
        # Determine which image and which holes to use
        if 'label_placement_idx' not in self.state:
            self.state['label_placement_idx'] = 0
            self.state['label_placement_holes'] = self.state['holes'][:]
            self.state['labeled_images'] = []
            self.state['label_positions'] = []
        img_idx = self.state['label_placement_idx']
        img_path = self.state['images'][img_idx]
        pil_img = Image.open(img_path)
        pil_img = pil_img.resize((500, 400), Image.ANTIALIAS)
        tk_img = ImageTk.PhotoImage(pil_img)
        canvas = Canvas(frame, width=500, height=400, bg="white")
        canvas.pack()
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        # Assign holes to this image
        start = 0
        for i in range(img_idx):
            start += self.state['img_hole_counts'][i]
        count = self.state['img_hole_counts'][img_idx]
        holes = self.state['holes'][start:start+count]
        drag_labels = []
        for i, label in enumerate(holes):
            drag_labels.append(DragLabel(canvas, label, 50+60*i, 30))
        def save_labeled_image():
            positions = {}
            for dl in drag_labels:
                x, y = dl.get_position()
                positions[dl.label] = (x, y)
            img = pil_img.copy()
            draw = ImageDraw.Draw(img)
            for label, (x, y) in positions.items():
                draw.text((x, y), label, fill="red")
            out_path = os.path.join('lib', f"labeled_img_{img_idx+1}.png")
            img.save(out_path)
            self.state['labeled_images'].append(out_path)
            self.state['label_positions'].append(positions)
            # Move to next image or next step
            self.state['label_placement_idx'] += 1
            if self.state['label_placement_idx'] < len(self.state['images']):
                self.show_step("label_placement")
            else:
                # Clean up state for next run
                del self.state['label_placement_idx']
                del self.state['label_placement_holes']
                self.show_step("torque_setting")
        ttk.Button(frame, text="Save Placement", command=save_labeled_image).pack(pady=10)
        self.current_frame = frame
        frame.tk_img = tk_img

    def show_torque_setting(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Set Torque Setting", font=("Arial", 16)).pack(pady=10)
        torque_var = tk.DoubleVar(value=float(self.config['DEFAULT']['default_target_torque']))
        ttk.Label(frame, text="Torque (Ncm-1):").pack()
        ttk.Entry(frame, textvariable=torque_var, width=10).pack(pady=2)
        def next_():
            self.state['torque'] = torque_var.get()
            self.show_step("run_test")
        ttk.Button(frame, text="Start Test", command=next_).pack(pady=10)
        self.current_frame = frame

    def show_run_test(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Running Test", font=("Arial", 16)).pack(pady=10)
        results = []
        sample_count = self.state['samples']
        # Collect all hole labels in order of images
        holes_per_image = [list(d.keys()) for d in self.state['label_positions']]
        torque = self.state['torque']
        for sample in range(sample_count):
            messagebox.showinfo("Sample", f"Prepare for sample {sample+1} of {sample_count}")
            for img_idx, img_path in enumerate(self.state['labeled_images']):
                pil_img = Image.open(img_path)
                tk_img = ImageTk.PhotoImage(pil_img)
                img_win = tk.Toplevel(self.root)
                img_win.title(f"Sample {sample+1} - Image {img_idx+1}")
                canvas = Canvas(img_win, width=500, height=400)
                canvas.pack()
                canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
                img_win.tk_img = tk_img
                positions = self.state['label_positions'][img_idx]
                for label in holes_per_image[img_idx]:
                    messagebox.showinfo("Test", f"Place screwdriver at hole {label} (Sample {sample+1}) and press OK to record.")
                    result = self.api.run_torque_test(label, torque)
                    result['sample'] = sample+1
                    results.append(result)
                img_win.destroy()
        self.state['results'] = results
        self.save_results_csv()
        self.show_step("show_plot")
        self.current_frame = frame

    def save_results_csv(self):
        results = self.state['results']
        os.makedirs('results', exist_ok=True)
        filename = f"results/torque_results_{self.state['com_port']}_{self.state['torque']}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['sample', 'hole_label', 'target_torque', 'actual_torque', 'timestamp'])
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        self.state['csv_file'] = filename

    def show_plot(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Test Results Plot", font=("Arial", 16)).pack(pady=10)
        results = self.state['results']
        samples = sorted(set(r['sample'] for r in results))
        holes = sorted(set(r['hole_label'] for r in results))
        fig, ax = plt.subplots()
        for sample in samples:
            vals = [r['actual_torque'] for r in results if r['sample']==sample]
            ax.plot(holes, vals, marker='o', label=f'Sample {sample}')
        ax.set_xlabel('Hole')
        ax.set_ylabel('Torque (Ncm-1)')
        ax.set_title('Torque Test Results')
        ax.legend()
        plot_path = f"results/torque_plot_{self.state['com_port']}_{self.state['torque']}.png"
        fig.savefig(plot_path)
        plt.close(fig)
        img = Image.open(plot_path)
        img = img.resize((500, 400), Image.ANTIALIAS)
        tk_img = ImageTk.PhotoImage(img)
        canvas = Canvas(frame, width=500, height=400)
        canvas.pack()
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        frame.tk_img = tk_img
        ttk.Label(frame, text=f"Plot and CSV saved to results/ folder.").pack(pady=10)
        ttk.Button(frame, text="Restart", command=lambda: self.show_step("connect")).pack(pady=10)
        self.current_frame = frame

if __name__ == "__main__":
    root = tk.Tk()
    app = TorqueTestWizard(root)
    root.mainloop()