from sqlalchemy import create_engine
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt

# Create database connection
engine = create_engine("sqlite:///moistureDB.db")

# Create the main window
root = tk.Tk()
root.geometry("800x600")  # Larger window for better graph visibility
root.title("Moisture Data Visualization")

def update_graph(*args):
    # Query to get the moisture data
    query = """
    SELECT id, moisture_percent, date_created 
    FROM MoistureContent 
    ORDER BY date_created DESC 
    LIMIT 50
    """
    
    # Read data into DataFrame
    df = pd.read_sql(query, engine)
    
    # Clear previous graph
    for widget in root.grid_slaves():
        if isinstance(widget, FigureCanvasTkAgg):
            widget.get_tk_widget().destroy()
    
    # Create new figure with larger size
    plt.figure(figsize=(10, 6))
    
    # Create the line plot
    plt.plot(df['id'], df['moisture_percent'], marker='o')
    
    # Customize the plot
    plt.title('Moisture Content Over Time')
    plt.xlabel('Reading ID')
    plt.ylabel('Moisture (%)')
    plt.grid(True)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Create canvas and show plot
    canvas = FigureCanvasTkAgg(plt.gcf(), root)
    canvas.draw()
    canvas.get_tk_widget().grid(row=1, column=0, padx=10, pady=10)

# Create refresh button
refresh_btn = ttk.Button(root, text="Refresh Data", command=update_graph)
refresh_btn.grid(row=0, column=0, padx=10, pady=10)

# Show initial graph
update_graph()

# Start the GUI
root.mainloop()