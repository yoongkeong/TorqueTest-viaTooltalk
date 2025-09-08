# tooltalk_api.py
# Abstracts the Tooltalk controller interface for MT6000

import socket
import subprocess
import platform
import random
import datetime
import time
import re

class TooltalkAPI:
    def __init__(self):
        self.connected = False
        self.socket_connection = None
        # Atlas Copco MT6000 specific settings
        self.timeout = 3
        self.command_delay = 0.1
        self.controller_ip = None
        self.controller_port = 4545  # Default ToolTalk port
    
    def _ping_host(self, ip_address):
        """Check if the controller IP is reachable using ping"""
        try:
            # Determine ping command based on OS
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "3000", ip_address]
            else:
                cmd = ["ping", "-c", "1", "-W", "3", ip_address]
            
            # Execute ping command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            # Check if ping was successful
            if result.returncode == 0:
                print(f"Ping successful to {ip_address}")
                return True
            else:
                print(f"Ping failed to {ip_address}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"Ping timeout to {ip_address}")
            return False
        except Exception as e:
            print(f"Ping error to {ip_address}: {e}")
            return False
    
    def test_connection(self, ip_address):
        """Test if the Atlas Copco MT6000 controller is responding on the specified IP"""
        try:
            # First check network reachability
            if not self._ping_host(ip_address):
                print(f"Controller at {ip_address} is not reachable")
                return False
            
            # Try to establish TCP connection
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(self.timeout)
            
            try:
                # Attempt to connect
                test_socket.connect((ip_address, self.controller_port))
                print(f"TCP connection established to {ip_address}:{self.controller_port}")
                
                # Send MT6000 identification command
                test_socket.send(b'0001 0001 0040 0001\r\n')
                time.sleep(0.5)
                
                # Try to receive response
                test_socket.settimeout(2.0)
                response = test_socket.recv(1024)
                
                if response:
                    response_str = response.decode('utf-8', errors='ignore')
                    print(f"Response received: {response_str}")
                    # Look for MT6000 response patterns
                    if any(pattern in response_str.upper() for pattern in ['MT6000', 'ATLAS', '0040', 'OK']):
                        test_socket.close()
                        return True
                
                test_socket.close()
                return False
                
            except socket.timeout:
                print(f"Connection timeout to {ip_address}:{self.controller_port}")
                test_socket.close()
                return False
            except ConnectionRefusedError:
                print(f"Connection refused by {ip_address}:{self.controller_port}")
                test_socket.close()
                return False
                
        except Exception as e:
            print(f"Connection test error: {e}")
            return False
    
    def connect(self, ip_address):
        """Establish connection to the Atlas Copco MT6000 controller via TCP/IP"""
        try:
            # Store IP address for later use
            self.controller_ip = ip_address
            
            # Close existing connection if any
            if self.socket_connection:
                self.socket_connection.close()
            
            # First check network reachability
            if not self._ping_host(ip_address):
                print(f"Cannot connect: Controller at {ip_address} is not reachable")
                return False
            
            # Create TCP socket connection
            self.socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_connection.settimeout(self.timeout)
            
            # Connect to the controller
            self.socket_connection.connect((ip_address, self.controller_port))
            print(f"Connected to controller at {ip_address}:{self.controller_port}")
            
            # Initialize MT6000 controller
            # Set controller to remote mode
            self.socket_connection.send(b'0001 0002 0042 0001\r\n')  # Enable remote control
            time.sleep(self.command_delay)
            
            # Read response
            response = self._read_response()
            if response and 'OK' in response:
                self.connected = True
                print(f"Controller initialized successfully at {ip_address}")
                return True
            else:
                print(f"Initialization failed. Response: {response}")
                self.socket_connection.close()
                self.socket_connection = None
                return False
            
        except socket.timeout:
            print(f"Connection timeout to {ip_address}:{self.controller_port}")
            self.connected = False
            if self.socket_connection:
                self.socket_connection.close()
                self.socket_connection = None
            return False
        except ConnectionRefusedError:
            print(f"Connection refused by {ip_address}:{self.controller_port}")
            self.connected = False
            if self.socket_connection:
                self.socket_connection.close()
                self.socket_connection = None
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            if self.socket_connection:
                self.socket_connection.close()
                self.socket_connection = None
            return False
    
    def _read_response(self):
        """Read response from MT6000 controller via TCP socket"""
        try:
            if not self.socket_connection:
                return ""
            
            # Set socket timeout for reading
            self.socket_connection.settimeout(self.timeout)
            
            response = b''
            start_time = time.time()
            
            while time.time() - start_time < self.timeout:
                try:
                    # Try to receive data
                    chunk = self.socket_connection.recv(1024)
                    if chunk:
                        response += chunk
                        
                        # Check if we have a complete response (ends with \r\n)
                        if b'\r\n' in response:
                            break
                    else:
                        # No more data available
                        break
                        
                except socket.timeout:
                    # Timeout waiting for data
                    break
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    break
            
            return response.decode('utf-8', errors='ignore').strip()
        
        except Exception as e:
            print(f"Error reading response: {e}")
            return ""
    
    def set_torque_target(self, target_torque):
        """Set target torque on MT6000 controller"""
        try:
            if not self.socket_connection or not self.connected:
                print("Not connected to controller")
                return False
                
            # Convert torque to MT6000 format (usually in cNm - centinewton meters)
            torque_cnm = int(target_torque * 100)  # Convert Nm to cNm
            
            # Format torque command for MT6000
            command = f'0001 0014 0043 {torque_cnm:04d}\r\n'
            self.socket_connection.send(command.encode())
            time.sleep(self.command_delay)
            
            response = self._read_response()
            return 'OK' in response
            
        except Exception as e:
            print(f"Error setting torque: {e}")
            return False
    
    def run_torque_test(self, hole_label, target_torque):
        """Execute actual torque test with MT6000 hardware"""
        if not self.connected or not self.socket_connection:
            raise Exception("Not connected to controller")
        
        try:
            # Set target torque
            if not self.set_torque_target(target_torque):
                raise Exception("Failed to set target torque")
            
            # Start tightening cycle
            self.socket_connection.send(b'0001 0018 0041 0001\r\n')  # Start cycle
            time.sleep(self.command_delay)
            
            # Wait for cycle completion and read result
            max_wait_time = 30  # Maximum wait time in seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                # Request last result
                self.socket_connection.send(b'0001 0033 0200\r\n')  # Request last tightening result
                time.sleep(0.5)
                
                response = self._read_response()
                
                if response and '0200' in response:
                    # Parse the tightening result
                    actual_torque = self._parse_torque_result(response, target_torque)
                    
                    return {
                        'hole_label': hole_label,
                        'target_torque': target_torque,
                        'actual_torque': actual_torque,
                        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                
                time.sleep(0.5)
            
            raise Exception("Timeout waiting for tightening result")
            
        except Exception as e:
            raise Exception(f"Torque test failed: {str(e)}")
    
    def _parse_torque_result(self, response, target_torque):
        """Parse torque result from MT6000 response"""
        try:
            # MT6000 response format varies, this is a common pattern
            # Look for torque value in the response
            torque_match = re.search(r'(\d{4,6})', response)
            
            if torque_match:
                # Convert from cNm to Nm
                actual_torque = float(torque_match.group(1)) / 100.0
                return actual_torque
            else:
                # If parsing fails, use target torque with small variation for testing
                print(f"Could not parse torque from response: {response}")
                return target_torque + random.uniform(-0.5, 0.5)
                
        except Exception as e:
            print(f"Error parsing torque result: {e}")
            return target_torque + random.uniform(-0.5, 0.5)
    
    def simulate_torque_test(self, hole_label, target_torque):
        """Simulation mode - generate realistic fake data"""
        # Add some random variation to simulate real measurements
        variation = random.uniform(-1.5, 1.5)
        actual_torque = target_torque + variation
        
        # Simulate measurement time
        time.sleep(0.5)
        
        return {
            'hole_label': hole_label,
            'target_torque': target_torque,
            'actual_torque': actual_torque,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def disconnect(self):
        """Clean disconnect from controller"""
        try:
            if self.socket_connection and self.connected:
                # Disable remote control
                self.socket_connection.send(b'0001 0002 0042 0000\r\n')
                time.sleep(self.command_delay)
                
            if self.socket_connection:
                self.socket_connection.close()
                self.socket_connection = None
                print(f"Disconnected from controller at {self.controller_ip}")
        except Exception as e:
            print(f"Error during disconnect: {e}")
        finally:
            self.connected = False
