import tkinter as tk
from tkinter import ttk, filedialog
import serial
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from models import MoistureContent, setup_database
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import queue
from datetime import datetime

class MoistureMonitorApp:
    def __init__(self, root):

        self.status_queue = queue.Queue()
        self.root = root
        self.root.title("Moisture Monitoring")
        self.root.geometry("800x600")

        # Serial setup
        self.ser = None
        self.is_connected = False
        self.serial_lock = threading.Lock()
        self.stop_monitoring = False
        self.data_collection_active = False
        self.loop_count = 0
        self.total_loops = 5

        # Database setup
        self.engine, self.Session = setup_database()
        self.is_collecting = False

        # GUI setup
        self.create_widgets()
        self.process_status_updates()

        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self.monitor_serial_connection)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def process_status_updates(self):
        while not self.status_queue.empty():
            text, color = self.status_queue.get_nowait()
            self.status_label.config(text=text, fg=color)
        self.root.after(100, self.process_status_updates)

    def create_widgets(self):

        # Status Frame
        self.status_frame = tk.Frame(self.root)
        self.status_frame.pack(expand=True, fill='x', padx=20, pady=20)
        
        self.status_label = tk.Label(
            self.status_frame, 
            text="ESP32 Status: Disconnected", 
            font=("Arial", 16)
        )
        self.status_label.pack(expand=True)

        # Progress Bar
        self.progress = ttk.Progressbar(
            self.status_frame,
            orient='horizontal',
            length=200,
            mode='determinate'
        )

        # Buttons
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(expand=True, fill='x', padx=20, pady=20)

        self.start_button = tk.Button(
            self.button_frame, 
            text="Start", 
            command=self.start_data_collection
        )
        self.start_button.pack(side='left', expand=True, padx=10)

        self.graph_button = tk.Button(
            self.button_frame, 
            text="Graph", 
            command=self.show_graph
        )
        self.graph_button.pack(side='left', expand=True, padx=10)

        self.export_button = tk.Button(
            self.button_frame,
            text="Export PDF",
            command=self.export_to_pdf
        )
        self.export_button.pack(side='right', expand=True, padx=10)
        self.led = tk.Canvas(self.status_frame, width=30, height=30)
        self.led.pack(pady=10)
        self.led_indicator = self.led.create_oval(5, 5, 25, 25, fill="gray")


    def export_to_csv(self):
        """Export database contents to CSV file"""
        try:
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension='.csv',
                filetypes=[("CSV files", "*.csv")],
                title="Save CSV file"
            )
            
            if file_path:
                session = self.Session()
                # Query all readings
                readings = session.query(MoistureContent).all()
                
                # Create dataframe
                data = {
                    'id': [r.id for r in readings],
                    'moisture_percent': [r.moisture_percent for r in readings],
                    'temperature': [r.temperature for r in readings],
                    'humidity': [r.humidity for r in readings],
                    'timestamp': [r.date_created for r in readings]
                }
                df = pd.DataFrame(data)
                
                # Save to CSV
                df.to_csv(file_path, index=False)
                session.close()
                
                self.update_status("Data exported successfully", "green")
        except Exception as e:
            self.update_status(f"Export failed: {str(e)}", "red")

    def start_data_collection(self):
        """Start data collection process"""
        if not self.is_connected:
            self.update_status("Cannot Start: Not Connected", "red")
            return

        if self.is_collecting:
            self.update_status("Already collecting data", "yellow")
            return

        try:
            with self.serial_lock:
                if not self.ser or not self.ser.is_open:
                    raise serial.SerialException("Device not connected")
                    
                self.loop_count = 0
                self.ser.write(b'S')
                self.is_collecting = True
                self.update_status("Data Collection: Started", "blue")
                self.show_progress()
                
                # Start the data collection thread
                self.data_collection_thread = threading.Thread(
                    target=self.collect_data
                )
                self.data_collection_thread.daemon = True
                self.data_collection_thread.start()

        except (serial.SerialException, OSError) as e:
            print(f"Start failed: {e}")
            self.handle_disconnection()
            self.update_status("Start Failed: Disconnected", "red")

    def collect_data(self):
        """Thread to collect data from ESP32"""
        start_time = time.time()
        timeout = 30  # 30 seconds timeout
        
        # Reset loop counter at start
        self.loop_count = 0
        
        while self.is_collecting and self.loop_count < self.total_loops:
            try:
                with self.serial_lock:
                    if not self.ser or not self.ser.is_open:
                        raise serial.SerialException("Device disconnected")
                        
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode().strip()
                        print(f"Received: {line}")  # Debug
                        
                        if line.startswith("Loop:"):
                            # Extract numeric value from "Loop: X"
                            try:
                                received_loop = int(line.split(":")[1].strip())
                                self.loop_count = received_loop
                                print(f"Updated loop: {self.loop_count}")
                                self.update_progress((self.loop_count / self.total_loops) * 100)
                            except ValueError:
                                print("Invalid loop message")
                                
                        elif line.startswith("Complete:"):
                            break
                            
                        elif not (line.startswith("Started") or line.startswith("Stopped")):
                            try:
                                parts = line.split(',')
                                if len(parts) == 3:
                                    session = self.Session()
                                    moisture_data = MoistureContent(
                                        moisture_percent=float(parts[0]),
                                        temperature=float(parts[1]),
                                        humidity=float(parts[2])
                                    )
                                    session.add(moisture_data)
                                    session.commit()
                                    session.close()
                            except ValueError as e:
                                print(f"Data parsing error: {e}")
                                
                # Check for timeout
                if time.time() - start_time > timeout:
                    print("Data collection timeout")
                    break
                    
                time.sleep(0.1)
                
            except (serial.SerialException, OSError) as e:
                print(f"Serial error: {e}")
                self.handle_disconnection()
                break

        # Completion handling
        self.is_collecting = False
        if self.loop_count >= self.total_loops:
            self.update_status("Data Collection: Complete", "green")
        else:
            self.update_status("Data Collection: Incomplete", "red")
        self.hide_progress()
    def update_status(self, text, color):
        """Enhanced thread-safe status updates"""
        def update_gui():
            current_text = self.status_label.cget("text")
            if current_text != text:  # Only update if changed
                self.status_label.config(text=text, fg=color)
                self.root.update_idletasks()  # Force GUI refresh
        
        self.root.after(0, update_gui)
        
    def monitor_serial_connection(self):
        """Improved connection monitoring with cooldown"""
        while not self.stop_monitoring:
            try:
                if not self.is_connected:
                    # Attempt connection with fresh port object
                    with self.serial_lock:
                        if self.ser:
                            self.ser.close()
                        self.ser = serial.Serial('COM3', 115200, timeout=1)
                        self.is_connected = True
                        self.root.after(0, self.update_status, 
                                    "ESP32 Status: Connected", "green")
                        print("Connected successfully")
                        time.sleep(2)  # Cooldown after connection
                else:
                    # Check connection status without CTS (more reliable)
                    with self.serial_lock:
                        if not self.ser.is_open:
                            raise serial.SerialException("Port closed")
                            
                        # Test with a safe command
                        self.ser.write(b'\x00')  # Null byte test
                        time.sleep(0.1)
                        
            except (serial.SerialException, OSError) as e:
                if self.is_connected:  # Only handle if we were connected
                    print(f"Disconnection detected: {str(e)}")
                    self.handle_disconnection()
                    time.sleep(2)  # Cooldown before reconnection attempt
                else:
                    time.sleep(1)  # Normal polling interval
                    
            except AttributeError:
                # Handle case where ser is None
                self.handle_disconnection()
                time.sleep(1)
                
            time.sleep(1)  # Base polling interval

    def handle_disconnection(self):

        def update_connection_state(self, connected):
            color = "green" if connected else "red"
            self.led.itemconfig(self.led_indicator, fill=color) 

        """Safer disconnection handling"""
        if self.is_connected:  # Only update if state changed
            self.is_connected = False
            self.root.after(0, self.update_status, 
                        "ESP32 Status: Disconnected", "red")
            
        with self.serial_lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()
                    print("Port closed properly")
            except Exception as e:
                print(f"Error closing port: {str(e)}")
            finally:
                self.ser = None  # Reset port object

        # Stop any ongoing collection
        if self.is_collecting:
            self.is_collecting = False
            self.root.after(0, self.hide_progress)
            self.root.after(0, self.update_status,
                        "Collection interrupted", "orange")

        def handle_disconnection(self):
            """Improved disconnection handling"""
            was_connected = self.is_connected
            self.is_connected = False
            
            if was_connected:
                self.root.after(0, self.update_status, 
                            "ESP32 Status: Disconnected", "red")
                
            with self.serial_lock:
                if self.ser and self.ser.is_open:
                    try:
                        self.ser.close()
                        print("Serial port closed properly")  # Debug
                    except Exception as e:
                        print(f"Error closing port: {str(e)}")  # Debug
                self.ser = None

            if self.is_collecting:
                self.is_collecting = False
                self.root.after(0, self.hide_progress)
                self.root.after(0, self.update_status,
                            "Connection lost during collection", "orange")
                
                # If data collection is active, stop it
                if self.is_collecting:
                    self.is_collecting = False
                    self.root.after(0, self.hide_progress)


    def show_progress(self):
        self.root.after(0, lambda: self.progress.pack(pady=10))
        self.root.after(0, lambda: self.progress.config(value=0))

    def update_progress(self, value):
        self.root.after(0, lambda: self.progress.config(value=value))

    def hide_progress(self):
        self.root.after(0, lambda: self.progress.pack_forget())

    def show_graph(self):
        """Show graph in the main thread"""
        try:
            # Create new window
            graph_window = tk.Toplevel(self.root)
            graph_window.title("Moisture Data Graph")
            graph_window.geometry("800x600")

            # Get data in a separate thread
            def fetch_data():
                session = self.Session()
                readings = session.query(MoistureContent).order_by(
                    MoistureContent.date_created.desc()
                ).limit(5).all()
                readings.reverse()
                session.close()
                return readings

            # Create and display graph in main thread
            def create_graph(readings):
                fig, ax = plt.subplots(figsize=(10, 6))
                
                data = {
                    'id': [r.id for r in readings],
                    'moisture_percent': [r.moisture_percent for r in readings],
                    'date': [r.date_created.strftime('%Y-%m-%d') for r in readings]
                }
                
                ax.plot(range(len(readings)), [r.moisture_percent for r in readings], 
                    marker='o', color='blue')
                ax.set_title('Moisture Content Over Time')
                ax.set_ylabel('Moisture (%)')
                ax.set_xlabel('Reading')
                
                ax.set_xticks(range(len(readings)))
                ax.set_xticklabels([f'ID:{r.id}\n{r.date_created.strftime("%Y-%m-%d")}' 
                                for r in readings], rotation=45)
                
                plt.tight_layout()
                
                canvas = FigureCanvasTkAgg(fig, graph_window)
                canvas.draw()
                canvas.get_tk_widget().pack(fill='both', expand=True)

            # Fetch data in background thread
            def async_fetch_and_create():
                readings = fetch_data()
                # Schedule graph creation in main thread
                self.root.after(0, lambda: create_graph(readings))

            # Start the background thread
            fetch_thread = threading.Thread(target=async_fetch_and_create)
            fetch_thread.daemon = True
            fetch_thread.start()
        
        except Exception as e:
            self.update_status(f"Graph creation failed: {str(e)}", "red")


    def export_to_pdf(self):
        """Export graph and data to PDF"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension='.pdf',
                filetypes=[("PDF files", "*.pdf")],
                title="Save PDF Report"
            )

            if file_path:
                # Get the data
                session = self.Session()
                readings = session.query(MoistureContent).order_by(
                    MoistureContent.date_created.desc()
                ).limit(5).all()
                readings.reverse()

                # Create PDF
                doc = SimpleDocTemplate(file_path, pagesize=letter)
                styles = getSampleStyleSheet()
                elements = []

                # Add title
                elements.append(Paragraph("Moisture Monitoring Report", styles['Title']))
                elements.append(Spacer(1, 20))

                # Create graph for PDF
                plt.figure(figsize=(8, 6))
                plt.plot(
                    range(len(readings)),
                    [r.moisture_percent for r in readings],
                    marker='o'
                )
                plt.title('Moisture Content Over Time')
                plt.ylabel('Moisture (%)')
                plt.xlabel('Reading')
                plt.xticks(
                    range(len(readings)),
                    [f'ID:{r.id}\n{r.date_created.strftime("%Y-%m-%d")}' for r in readings],
                    rotation=45
                )
                plt.tight_layout()

                # Save graph to buffer
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
                plt.close()

                # Add image to PDF
                from reportlab.platypus import Image
                img = Image(buf)
                img.drawHeight = 300
                img.drawWidth = 500
                elements.append(img)
                elements.append(Spacer(1, 20))

                # Add table
                data = [['ID', 'Moisture %', 'Temperature', 'Humidity', 'Date']]
                for reading in readings:
                    data.append([
                        str(reading.id),
                        f"{reading.moisture_percent:.2f}%",
                        f"{reading.temperature:.2f}°C",
                        f"{reading.humidity:.2f}%",
                        reading.date_created.strftime("%Y-%m-%d %H:%M:%S")
                    ])

                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(table)

                # Build PDF
                doc.build(elements)
                buf.close()
                session.close()

                self.update_status("PDF exported successfully", "green")

        except Exception as e:
            self.update_status(f"Export failed: {str(e)}", "red")

    def on_closing(self):
        """Cleanup when window closes"""
        self.stop_monitoring = True
        with self.serial_lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
        self.root.destroy()

    def update_status(self, text, color):
        """Thread-safe GUI update"""
        self.root.after(0, lambda: self.status_label.config(text=text, fg=color))
    
    def find_esp32_port(self):
        """Scan for available COM ports"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "USB" in port.description.upper() or "SERIAL" in port.description.upper():
                return port.device
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = MoistureMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()