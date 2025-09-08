# torque_graph.py
# Live torque graphing and data capture module for Atlas Copco screwdriver

import threading
import time
import queue
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import os
import csv
from datetime import datetime
import random

class TorqueGraph:
    def __init__(self, parent_window=None, enable_gui=True):
        """
        Initialize the torque graphing system
        
        Args:
            parent_window: Tkinter parent window (optional)
            enable_gui: Whether to show GUI windows (False for headless mode)
        """
        self.parent_window = parent_window
        self.enable_gui = enable_gui
        self.is_capturing = False
        self.capture_thread = None
        self.data_queue = queue.Queue()
        self.torque_data = []
        self.angle_data = []
        self.time_data = []
        self.start_time = None
        
        # GUI components
        self.graph_window = None
        self.fig = None
        self.ax = None
        self.canvas = None
        self.ani = None
        
        # Configuration
        self.sample_rate = 10  # Hz
        self.max_samples = 1000
        self.timeout_seconds = 30
        
    def start_capture(self, title="Live Torque Graph", save_to_file=True):
        """
        Start live torque capture and display
        
        Args:
            title: Window title for the graph
            save_to_file: Whether to save data to CSV file
        """
        if self.is_capturing:
            return False
            
        # Reset data
        self.torque_data = []
        self.angle_data = []
        self.time_data = []
        self.start_time = time.time()
        self.is_capturing = True
        
        # Start capture thread
        self.capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True
        )
        self.capture_thread.start()
        
        if self.enable_gui:
            self._create_graph_window(title)
            self._start_animation()
        
        return True
    
    def stop_capture(self, save_to_file=True):
        """
        Stop live torque capture
        
        Args:
            save_to_file: Whether to save captured data to CSV
        """
        if not self.is_capturing:
            return None
            
        self.is_capturing = False
        
        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        
        # Stop animation
        if self.ani:
            self.ani.event_source.stop()
        
        # Save data if requested
        if save_to_file and self.torque_data:
            filename = self._save_data_to_csv()
            return filename
        
        return None
    
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        while self.is_capturing:
            try:
                # Simulate torque and angle data
                # In real implementation, this would read from the screwdriver
                current_time = time.time() - self.start_time
                
                # Generate realistic torque data with some variation
                base_torque = 20.0 + 5.0 * np.sin(current_time * 2) + random.uniform(-1, 1)
                angle = current_time * 30  # Simulate angle progression
                
                # Add data to queue for thread-safe access
                self.data_queue.put({
                    'time': current_time,
                    'torque': base_torque,
                    'angle': angle
                })
                
                # Limit data size
                if len(self.torque_data) > self.max_samples:
                    self.torque_data.pop(0)
                    self.angle_data.pop(0)
                    self.time_data.pop(0)
                
                time.sleep(1.0 / self.sample_rate)
                
            except Exception as e:
                print(f"Error in capture loop: {e}")
                break
    
    def _create_graph_window(self, title):
        """Create the graph window"""
        if not self.enable_gui:
            return
            
        self.graph_window = tk.Toplevel(self.parent_window) if self.parent_window else tk.Tk()
        self.graph_window.title(title)
        self.graph_window.geometry("800x600")
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Torque (Ncm)')
        self.ax.set_title('Live Torque Measurement')
        self.ax.grid(True, alpha=0.3)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, self.graph_window)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add control buttons
        button_frame = ttk.Frame(self.graph_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Stop Capture", 
                  command=self._stop_button_clicked).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(button_frame, text="Capturing...")
        self.status_label.pack(side=tk.LEFT, padx=10)
    
    def _start_animation(self):
        """Start the matplotlib animation for live updates"""
        if not self.enable_gui or not self.fig:
            return
            
        self.ani = animation.FuncAnimation(
            self.fig, self._update_graph, interval=100, blit=False
        )
    
    def _update_graph(self, frame):
        """Update the graph with new data"""
        if not self.enable_gui or not self.ax:
            return
            
        # Get new data from queue
        new_data_count = 0
        while not self.data_queue.empty():
            try:
                data = self.data_queue.get_nowait()
                self.time_data.append(data['time'])
                self.torque_data.append(data['torque'])
                self.angle_data.append(data['angle'])
                new_data_count += 1
            except queue.Empty:
                break
        
        if new_data_count > 0:
            # Clear and redraw
            self.ax.clear()
            self.ax.set_xlabel('Time (s)')
            self.ax.set_ylabel('Torque (Ncm)')
            self.ax.set_title('Live Torque Measurement')
            self.ax.grid(True, alpha=0.3)
            
            if self.time_data:
                self.ax.plot(self.time_data, self.torque_data, 'b-', linewidth=2, label='Torque')
                
                # Add angle on secondary y-axis if available
                if self.angle_data:
                    ax2 = self.ax.twinx()
                    ax2.plot(self.time_data, self.angle_data, 'r--', alpha=0.7, label='Angle')
                    ax2.set_ylabel('Angle (degrees)', color='r')
                    ax2.tick_params(axis='y', labelcolor='r')
                
                self.ax.legend(loc='upper left')
                
                # Update status
                if hasattr(self, 'status_label'):
                    max_torque = max(self.torque_data) if self.torque_data else 0
                    self.status_label.config(text=f"Capturing... Max: {max_torque:.1f} Ncm")
    
    def _stop_button_clicked(self):
        """Handle stop button click"""
        if self.graph_window:
            self.graph_window.destroy()
        self.stop_capture()
    
    def _save_data_to_csv(self):
        """Save captured data to CSV file"""
        if not self.torque_data:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results/live_torque_{timestamp}.csv"
        
        os.makedirs('results', exist_ok=True)
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Time (s)', 'Torque (Ncm)', 'Angle (deg)'])
            
            for i in range(len(self.time_data)):
                writer.writerow([
                    self.time_data[i],
                    self.torque_data[i],
                    self.angle_data[i] if i < len(self.angle_data) else 0
                ])
        
        return filename
    
    def get_latest_torque(self):
        """Get the most recent torque reading"""
        return self.torque_data[-1] if self.torque_data else 0.0
    
    def get_max_torque(self):
        """Get the maximum torque recorded"""
        return max(self.torque_data) if self.torque_data else 0.0
    
    def get_data_summary(self):
        """Get summary statistics of captured data"""
        if not self.torque_data:
            return None
            
        return {
            'samples': len(self.torque_data),
            'duration': self.time_data[-1] - self.time_data[0] if len(self.time_data) > 1 else 0,
            'max_torque': max(self.torque_data),
            'min_torque': min(self.torque_data),
            'avg_torque': sum(self.torque_data) / len(self.torque_data)
        }


class TestPhaseDialog:
    """Dialog for the Test Phase after connection confirmation"""
    
    def __init__(self, parent, api, simulation_mode=False):
        self.parent = parent
        self.api = api
        self.simulation_mode = simulation_mode
        self.result = None
        self.torque_graph = None
        
    def show(self):
        """Show the test phase dialog"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Test Phase - Trigger Test")
        dialog.geometry("600x400")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        ttk.Label(frame, text="Test Phase - Trigger Test", 
                 font=("Arial", 16, "bold")).pack(pady=10)
        
        instruction_text = (
            "Please press and hold the screwdriver trigger to capture live torque data.\n\n"
            "The graph will show real-time torque measurements while the trigger is pressed.\n"
            "Release the trigger when you're satisfied with the test."
        )
        
        ttk.Label(frame, text=instruction_text, 
                 justify=tk.CENTER, wraplength=500).pack(pady=10)
        
        # Status
        self.status_label = ttk.Label(frame, text="Ready to start test", 
                                    foreground="blue")
        self.status_label.pack(pady=10)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        self.start_button = ttk.Button(button_frame, text="Start Test", 
                                     command=lambda: self._start_test(dialog))
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Skip Test", 
                  command=lambda: self._skip_test(dialog)).pack(side=tk.LEFT, padx=5)
        
        # Wait for dialog to close
        dialog.wait_window()
        return self.result
    
    def _start_test(self, dialog):
        """Start the trigger test"""
        self.start_button.config(state='disabled')
        self.status_label.config(text="Press and hold the screwdriver trigger now...", 
                               foreground="orange")
        
        # Initialize torque graph
        self.torque_graph = TorqueGraph(dialog, enable_gui=True)
        
        # Start capture
        if self.torque_graph.start_capture("Test Phase - Live Torque"):
            self.status_label.config(text="Capturing torque data... Release trigger when done.", 
                                   foreground="green")
            
            # In a real implementation, this would wait for actual trigger press
            # For now, we'll simulate a test duration
            dialog.after(5000, lambda: self._complete_test(dialog))
        else:
            self.status_label.config(text="Failed to start capture", foreground="red")
            self.start_button.config(state='normal')
    
    def _complete_test(self, dialog):
        """Complete the test and show results"""
        if self.torque_graph:
            filename = self.torque_graph.stop_capture()
            
            if filename:
                summary = self.torque_graph.get_data_summary()
                if summary:
                    result_text = (
                        f"Test completed successfully!\n\n"
                        f"Samples captured: {summary['samples']}\n"
                        f"Duration: {summary['duration']:.1f} seconds\n"
                        f"Max torque: {summary['max_torque']:.1f} Ncm\n"
                        f"Average torque: {summary['avg_torque']:.1f} Ncm\n\n"
                        f"Data saved to: {filename}"
                    )
                    
                    self.status_label.config(text=result_text, foreground="green")
                    
                    # Show confirmation dialog
                    if messagebox.askyesno("Test Complete", 
                                         "Did the live graph appear correctly?\n\n" + result_text):
                        self.result = True
                    else:
                        self.result = False
                else:
                    self.result = False
            else:
                self.result = False
        
        # Re-enable button and add continue option
        self.start_button.config(state='normal', text='Continue')
        self.start_button.config(command=lambda: self._continue(dialog))
    
    def _skip_test(self, dialog):
        """Skip the test phase"""
        self.result = None
        dialog.destroy()
    
    def _continue(self, dialog):
        """Continue after test completion"""
        dialog.destroy()
