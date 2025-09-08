import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Canvas
from PIL import Image, ImageTk, ImageDraw
import configparser
import os
import csv
import shutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tooltalk_api import TooltalkAPI
from torque_graph import TorqueGraph, TestPhaseDialog

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
                'output_directory': 'results',
                'enable_live_graphs': 'true',
                'enable_test_phase': 'true',
                'controller_ip': '192.168.1.100',
                'controller_port': '4545',
                'connection_timeout': '5'
            }
            with open(self.config_file, 'w') as f:
                self.config.write(f)
        self.config.read(self.config_file)

    def init_folders(self):
        os.makedirs('lib', exist_ok=True)
        os.makedirs('lib/preset', exist_ok=True)
        os.makedirs('results', exist_ok=True)

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = None

    def show_step(self, step):
        self.clear_frame()
        if step == "connect":
            self.show_connect()
        elif step == "test_phase":
            self.show_test_phase()
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
        
        # Simulation mode toggle
        simulation_frame = ttk.Frame(frame)
        simulation_frame.pack(pady=10)
        
        simulation_var = tk.BooleanVar()
        ttk.Checkbutton(simulation_frame, text="Simulation Mode (No Hardware Required)", 
                       variable=simulation_var,
                       command=lambda: self.toggle_simulation_mode(simulation_var.get(), connection_frame)).pack()
        
        # Connection frame (shown only when not in simulation mode)
        connection_frame = ttk.Frame(frame)
        connection_frame.pack(pady=10, fill=tk.X)
        
        # IP address configuration
        ip_frame = ttk.Frame(connection_frame)
        ip_frame.pack(pady=5, fill=tk.X)
        
        ttk.Label(ip_frame, text="Controller IP Address:").pack(anchor=tk.W)
        
        ip_var = tk.StringVar(value=self.config['DEFAULT']['controller_ip'])
        ip_entry = ttk.Entry(ip_frame, textvariable=ip_var, width=20)
        ip_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        def test_ip_connectivity():
            """Test IP address connectivity"""
            ip_address = ip_var.get().strip()
            if not ip_address:
                status_lbl.config(text="Please enter an IP address", foreground="orange")
                return
            
            status_lbl.config(text="Testing IP connectivity...", foreground="orange")
            self.root.update()
            
            try:
                if self.api.test_connection(ip_address):
                    status_lbl.config(text=f"Controller reachable at {ip_address}", foreground="green")
                else:
                    status_lbl.config(text=f"Controller not reachable at {ip_address}", foreground="red")
            except Exception as e:
                status_lbl.config(text=f"Connection test error: {str(e)}", foreground="red")
        
        ttk.Button(ip_frame, text="Test Connection", command=test_ip_connectivity).pack(side=tk.LEFT)
        
        # Create status label
        status_lbl = ttk.Label(connection_frame, text="Not connected", foreground="red")
        status_lbl.pack(pady=5)
        
        # Add test connection button (redundant with IP test, but keeping for compatibility)
        def test_connection():
            ip_address = ip_var.get().strip()
            if not ip_address:
                messagebox.showerror("Input Error", "Please enter an IP address.")
                return
            
            status_lbl.config(text="Testing connection...", foreground="orange")
            self.root.update()
            
            try:
                if self.api.test_connection(ip_address):
                    status_lbl.config(text="Connection verified!", foreground="green")
                else:
                    status_lbl.config(text="Connection failed", foreground="red")
                    messagebox.showerror("Connection Failed", 
                        f"Could not connect to Tooltalk controller at {ip_address}.\n\n"
                        "Please check:\n"
                        "• Controller is powered on\n"
                        "• Correct IP address entered\n"
                        "• Network connectivity\n"
                        "• Controller is not in use by another application")
            except Exception as e:
                status_lbl.config(text="Connection error", foreground="red")
                messagebox.showerror("Connection Error", f"Error testing connection: {str(e)}")
        
        ttk.Button(connection_frame, text="Test Connection", command=test_connection).pack(pady=5)
        
        def connect():
            if simulation_var.get():
                # Simulation mode - skip actual connection
                status_lbl.config(text="Simulation Mode Active", foreground="blue")
                self.state['com_port'] = "SIM"
                self.state['simulation_mode'] = True
                
                # Check if test phase is enabled
                if self.config.getboolean('DEFAULT', 'enable_test_phase', fallback=True):
                    self.root.after(800, lambda: self.show_step("test_phase"))
                else:
                    self.root.after(800, lambda: self.show_step("hole_sample"))
            else:
                # Real mode - verify connection before proceeding
                ip_address = ip_var.get().strip()
                if not ip_address:
                    messagebox.showerror("Input Error", "Please enter an IP address.")
                    return
                
                status_lbl.config(text="Connecting...", foreground="orange")
                self.root.update()
                
                try:
                    # First test the connection
                    if not self.api.test_connection(ip_address):
                        status_lbl.config(text="Connection failed", foreground="red")
                        messagebox.showerror("Connection Failed", 
                            f"Could not establish connection to Tooltalk controller at {ip_address}.\n\n"
                            "Please verify:\n"
                            "• Controller is powered on and ready\n"
                            "• Correct IP address is entered\n"
                            "• Network connectivity is working\n"
                            "• Controller is not being used by another application\n\n"
                            "Check network settings:\n"
                            "1. Verify controller IP address in network settings\n"
                            "2. Ensure controller and PC are on same network\n"
                            "3. Check firewall settings")
                        return
                    
                    # Then establish the actual connection
                    if self.api.connect(ip_address):
                        status_lbl.config(text="Connected and Ready", foreground="green")
                        self.state['controller_ip'] = ip_address
                        self.state['simulation_mode'] = False
                        # Save the working IP to config
                        self.config['DEFAULT']['controller_ip'] = ip_address
                        with open(self.config_file, 'w') as f:
                            self.config.write(f)
                        
                        # Check if test phase is enabled
                        if self.config.getboolean('DEFAULT', 'enable_test_phase', fallback=True):
                            self.root.after(800, lambda: self.show_step("test_phase"))
                        else:
                            self.root.after(800, lambda: self.show_step("hole_sample"))
                    else:
                        status_lbl.config(text="Connection failed", foreground="red")
                        messagebox.showerror("Connection Failed", 
                            "Connection test passed but could not establish working connection.\n"
                            "Please try again or contact technical support.")
                        
                except Exception as e:
                    status_lbl.config(text="Connection error", foreground="red")
                    messagebox.showerror("Connection Error", f"Error connecting to controller: {str(e)}")
        
        connect_btn = ttk.Button(frame, text="Connect & Continue", command=connect)
        connect_btn.pack(pady=10)
        
        # Store references for toggling
        self.connection_frame = connection_frame
        self.simulation_var = simulation_var
        
        self.current_frame = frame

    def show_test_phase(self):
        """Show the Test Phase dialog after connection confirmation"""
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Test Phase", font=("Arial", 16)).pack(pady=10)
        ttk.Label(frame, text="Testing screwdriver trigger and live torque capture...", 
                 font=("Arial", 12)).pack(pady=10)
        
        # Show the test phase dialog
        simulation_mode = self.state.get('simulation_mode', False)
        test_dialog = TestPhaseDialog(self.root, self.api, simulation_mode)
        result = test_dialog.show()
        
        # Continue to next step regardless of test result
        self.show_step("hole_sample")

    def toggle_simulation_mode(self, is_simulation, connection_frame):
        if is_simulation:
            connection_frame.pack_forget()
        else:
            connection_frame.pack(pady=10, fill=tk.X)

    def show_hole_sample(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Define Screw Holes and Samples", font=("Arial", 16)).pack(pady=10)
        
        # Preset selection
        use_preset_var = tk.BooleanVar()
        preset_frame = ttk.Frame(frame)
        preset_frame.pack(pady=10, fill=tk.X)
        
        ttk.Checkbutton(preset_frame, text="Use Preset", variable=use_preset_var, 
                       command=lambda: self.toggle_preset_mode(use_preset_var.get(), manual_frame, preset_config_frame)).pack(anchor=tk.W)
        
        # Preset configuration frame
        preset_config_frame = ttk.Frame(frame)
        ttk.Label(preset_config_frame, text="Select Preset:").pack(anchor=tk.W)
        
        preset_var = tk.StringVar()
        preset_combo = ttk.Combobox(preset_config_frame, textvariable=preset_var, 
                                   values=["scube lid GigE"], state="readonly", width=20)
        preset_combo.pack(pady=2, anchor=tk.W)
        preset_combo.set("scube lid GigE")  # Default selection
        
        ttk.Label(preset_config_frame, text="Number of samples:").pack(anchor=tk.W, pady=(10, 0))
        preset_samples_var = tk.IntVar(value=1)
        ttk.Entry(preset_config_frame, textvariable=preset_samples_var, width=5).pack(pady=2, anchor=tk.W)
        
        # Manual configuration frame
        manual_frame = ttk.Frame(frame)
        manual_frame.pack(pady=10, fill=tk.X)
        
        holes_var = tk.IntVar(value=5)
        samples_var = tk.IntVar(value=1)
        ttk.Label(manual_frame, text="Number of screw holes (A, B, ...):").pack(anchor=tk.W)
        ttk.Entry(manual_frame, textvariable=holes_var, width=5).pack(pady=2, anchor=tk.W)
        ttk.Label(manual_frame, text="Number of samples:").pack(anchor=tk.W)
        ttk.Entry(manual_frame, textvariable=samples_var, width=5).pack(pady=2, anchor=tk.W)
        
        def next_():
            if use_preset_var.get():
                # Handle preset mode
                preset_name = preset_var.get()
                samples = preset_samples_var.get()
                
                if not preset_name:
                    messagebox.showerror("Input Error", "Please select a preset.")
                    return
                
                if samples < 1:
                    messagebox.showerror("Input Error", "Number of samples must be at least 1.")
                    return
                
                # Load preset configuration
                if preset_name == "scube lid GigE":
                    preset_files = [
                        "ace_GigE_Lid_A_B_C_D_G.png",
                        "ace_GigE_Lid_E_F.png"
                    ]
                    holes = ['A', 'B', 'C', 'D', 'E', 'F', 'G']  # All holes for this preset
                    img_hole_counts = [5, 2]  # First image has 5 holes (A,B,C,D,G), second has 2 (E,F)
                else:
                    messagebox.showerror("Error", "Unknown preset selected.")
                    return
                
                # Check if preset files exist
                preset_dir = "lib/preset"
                if not os.path.exists(preset_dir):
                    messagebox.showerror("Error", f"Preset directory '{preset_dir}' not found.")
                    return
                
                image_paths = []
                for filename in preset_files:
                    filepath = os.path.join(preset_dir, filename)
                    if not os.path.exists(filepath):
                        messagebox.showerror("Error", f"Preset file '{filename}' not found in '{preset_dir}'.")
                        return
                    image_paths.append(filepath)
                
                # Set state for preset
                self.state['holes'] = holes
                self.state['samples'] = samples
                self.state['images'] = image_paths
                self.state['img_hole_counts'] = img_hole_counts
                self.state['using_preset'] = True
                self.state['preset_name'] = preset_name
                
                # Skip image upload and go directly to label placement
                self.show_step("label_placement")
            else:
                # Handle manual mode
                n = holes_var.get()
                s = samples_var.get()
                if n < 1 or s < 1 or n > 26:
                    messagebox.showerror("Input Error", "Number of holes/samples must be 1-26.")
                    return
                self.state['holes'] = [chr(65+i) for i in range(n)]
                self.state['samples'] = s
                self.state['using_preset'] = False
                self.show_step("image_upload")
        
        ttk.Button(frame, text="Next", command=next_).pack(pady=20)
        
        # Store references for toggling
        self.preset_config_frame = preset_config_frame
        self.manual_frame = manual_frame
        
        # Initially show manual mode
        self.toggle_preset_mode(False, manual_frame, preset_config_frame)
        
        self.current_frame = frame

    def toggle_preset_mode(self, use_preset, manual_frame, preset_config_frame):
        if use_preset:
            manual_frame.pack_forget()
            preset_config_frame.pack(pady=10, fill=tk.X)
        else:
            preset_config_frame.pack_forget()
            manual_frame.pack(pady=10, fill=tk.X)

    def show_image_upload(self):
        # Skip this step if using preset
        if self.state.get('using_preset', False):
            self.show_step("label_placement")
            return
        
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
        # Skip label placement if using preset (images already have labels)
        if self.state.get('using_preset', False):
            self.show_step("torque_setting")
            return
            
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
        pil_img = pil_img.resize((500, 400), Image.LANCZOS)
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
        torque = self.state['torque']
        simulation_mode = self.state.get('simulation_mode', False)
        
        # Handle preset vs manual mode differently
        if self.state.get('using_preset', False):
            # For presets, use the original preset images and predefined hole order
            preset_name = self.state['preset_name']
            if preset_name == "scube lid GigE":
                # Define holes per image for this preset
                holes_per_image = [
                    ['A', 'B', 'C', 'D', 'G'],  # First image: ace_GigE_Lid_A_B_C_D_G.png
                    ['E', 'F']                   # Second image: ace_GigE_Lid_E_F.png
                ]
            else:
                messagebox.showerror("Error", "Unknown preset configuration.")
                return
            
            for sample in range(sample_count):
                messagebox.showinfo("Sample", f"Prepare for sample {sample+1} of {sample_count}")
                for img_idx, img_path in enumerate(self.state['images']):
                    pil_img = Image.open(img_path)
                    pil_img = pil_img.resize((500, 400), Image.LANCZOS)
                    tk_img = ImageTk.PhotoImage(pil_img)
                    img_win = tk.Toplevel(self.root)
                    img_win.title(f"Sample {sample+1} - Image {img_idx+1}")
                    canvas = Canvas(img_win, width=500, height=400)
                    canvas.pack()
                    canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
                    img_win.tk_img = tk_img
                    
                    # Use predefined holes for this image
                    for label in holes_per_image[img_idx]:
                        if simulation_mode:
                            messagebox.showinfo("Simulation", f"Simulating torque test for hole {label} (Sample {sample+1})")
                            result = self.api.simulate_torque_test(label, torque)
                        else:
                            messagebox.showinfo("Test", f"Place screwdriver at hole {label} (Sample {sample+1}) and press OK to record.")
                            result = self.api.run_torque_test(label, torque)
                        result['sample'] = sample+1
                        results.append(result)
                        
                        # Show live graph if enabled
                        if self.config.getboolean('DEFAULT', 'enable_live_graphs', fallback=True):
                            self._show_live_graph_for_test(label, sample+1, result)
                    img_win.destroy()
        else:
            # For manual mode, use labeled images and positions
            holes_per_image = [list(d.keys()) for d in self.state['label_positions']]
            
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
                        if simulation_mode:
                            messagebox.showinfo("Simulation", f"Simulating torque test for hole {label} (Sample {sample+1})")
                            result = self.api.simulate_torque_test(label, torque)
                        else:
                            messagebox.showinfo("Test", f"Place screwdriver at hole {label} (Sample {sample+1}) and press OK to record.")
                            result = self.api.run_torque_test(label, torque)
                        result['sample'] = sample+1
                        results.append(result)
                        
                        # Show live graph if enabled
                        if self.config.getboolean('DEFAULT', 'enable_live_graphs', fallback=True):
                            self._show_live_graph_for_test(label, sample+1, result)
                    img_win.destroy()
        
        self.state['results'] = results
        self.save_results_csv()
        self.show_step("show_plot")
        self.current_frame = frame

    def _show_live_graph_for_test(self, hole_label, sample_num, result):
        """Show a live graph for a completed torque test"""
        try:
            # Create a simple graph showing the test result
            graph_window = tk.Toplevel(self.root)
            graph_window.title(f"Torque Test Result - Hole {hole_label} (Sample {sample_num})")
            graph_window.geometry("600x400")
            
            # Create a simple bar chart showing the result
            fig, ax = plt.subplots(figsize=(8, 5))
            
            # Create a simple visualization of the torque measurement
            target_torque = result['target_torque']
            actual_torque = result['actual_torque']
            
            # Bar chart
            bars = ax.bar(['Target', 'Actual'], [target_torque, actual_torque], 
                         color=['lightblue', 'lightgreen'], alpha=0.7)
            
            # Add value labels on bars
            for bar, value in zip(bars, [target_torque, actual_torque]):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{value:.1f} Ncm', ha='center', va='bottom')
            
            ax.set_ylabel('Torque (Ncm)')
            ax.set_title(f'Hole {hole_label} - Sample {sample_num}\nTarget: {target_torque:.1f} Ncm, Actual: {actual_torque:.1f} Ncm')
            ax.grid(True, alpha=0.3)
            
            # Add canvas to window
            canvas = FigureCanvasTkAgg(fig, graph_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Add close button
            ttk.Button(graph_window, text="Close", 
                      command=graph_window.destroy).pack(pady=10)
            
            # Auto-close after 5 seconds
            graph_window.after(5000, graph_window.destroy)
            
        except Exception as e:
            print(f"Error showing live graph: {e}")

    def save_results_csv(self):
        results = self.state['results']
        os.makedirs('results', exist_ok=True)
        # Use IP address or simulation mode identifier for filename
        connection_id = self.state.get('controller_ip', self.state.get('com_port', 'SIM'))
        filename = f"results/torque_results_{connection_id}_{self.state['torque']}.csv"
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
        # Use IP address or simulation mode identifier for plot filename
        connection_id = self.state.get('controller_ip', self.state.get('com_port', 'SIM'))
        plot_path = f"results/torque_plot_{connection_id}_{self.state['torque']}.png"
        fig.savefig(plot_path)
        plt.close(fig)
        img = Image.open(plot_path)
        img = img.resize((500, 400), Image.LANCZOS)
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