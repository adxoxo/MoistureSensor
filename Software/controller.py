import serial
import time
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Moisture, Base

def connect_serial():
    """Attempt to connect to ESP32 via serial"""
    try:
        ser = serial.Serial(
            port='COM3',
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        print("Successfully connected to ESP32")
        time.sleep(2)  # Give time for serial connection to stabilize
        ser.flush()    # Flush any leftover data
        return ser
    except serial.SerialException as e:
        print(f"Error connecting to serial port: {e}")
        return None

def parse_data(line):
    """Parse the incoming data string from ESP32"""
    try:
        # Print raw data for debugging
        print(f"Raw bytes received: {line}")
        
        # Try different decodings if utf-8 fails
        try:
            decoded_line = line.decode('utf-8')
        except UnicodeDecodeError:
            try:
                decoded_line = line.decode('ascii', errors='ignore')
            except:
                decoded_line = line.decode('latin-1')
        
        print(f"Decoded line: {decoded_line}")
        
        # Check if this is a status message
        if "Started" in decoded_line or "Stopped" in decoded_line:
            return {"status": decoded_line.strip()}
            
        # Clean the data and split by comma
        cleaned_line = decoded_line.strip()
        if not cleaned_line:  # Skip empty lines
            return None
            
        values = cleaned_line.split(',')
        
        # Check if we have all required values
        if len(values) != 3:  # Expecting 3 values
            print(f"Warning: Expected 3 values, but got {len(values)}")
            return None
            
        # Convert values to appropriate types
        try:
            return {
                'moisture_percent': float(values[0]),
                'temperature': float(values[1]),
                'humidity': float(values[2])
            }
        except (ValueError, IndexError) as e:
            print(f"Error converting values: {e}")
            return None
            
    except Exception as e:
        print(f"Error parsing data: {e}")
        print(f"Problematic line: {line}")
        return None

def main():
    # Database connection
    engine = create_engine('sqlite:///moistureDB.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Serial connection
    ser = connect_serial()
    if not ser:
        return
    
    print("\nCommands:")
    print("s - Start data collection")
    print("x - Stop data collection")
    print("q - Quit program")
    print("\nWaiting for command...")
    
    try:
        while True:
            # Check for user input
            if input_available():  # You'll need to implement this based on your OS
                command = input().lower()
                
                if command == 's':
                    ser.write(b'S')  # Send start command
                    print("Sending start command...")
                
                elif command == 'x':
                    ser.write(b'X')  # Send stop command
                    print("Sending stop command...")
                
                elif command == 'q':
                    print("Quitting...")
                    break
            
            # Check for serial data
            if ser.in_waiting:
                try:
                    line = ser.readline()
                    if line:
                        data = parse_data(line)
                        
                        if data:
                            # Check if this is a status message
                            if "status" in data:
                                print(f"ESP32 Status: {data['status']}")
                                continue
                                
                            # Create new moisture reading
                            moisture_reading = Moisture(
                                moisture_percent=data['moisture_percent'],
                                date_created=datetime.now()
                            )
                            moisture_reading.temperature = data['temperature']
                            moisture_reading.humidity = data['humidity']
                            
                            # Save to database
                            try:
                                session.add(moisture_reading)
                                session.commit()
                                print(f"Saved reading: "
                                      f"Moisture: {data['moisture_percent']}%, "
                                      f"Temp: {data['temperature']}°C, "
                                      f"Humidity: {data['humidity']}%")
                            except Exception as e:
                                print(f"Error saving to database: {e}")
                                session.rollback()
                                
                except Exception as e:
                    print(f"Unexpected error: {e}")
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\nStopping data collection...")
    finally:
        # Send stop command before closing
        ser.write(b'X')
        time.sleep(0.5)  # Give ESP32 time to process the stop command
        ser.close()
        session.close()
        print("Connections closed")

def input_available():
    """Check if input is available (implementation depends on your OS)"""
    import sys
    import select
    
    # For Windows
    if sys.platform == 'win32':
        import msvcrt
        return msvcrt.kbhit()
    
    # For Unix-like systems
    else:
        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        return len(rlist) > 0

if __name__ == "__main__":
    main()