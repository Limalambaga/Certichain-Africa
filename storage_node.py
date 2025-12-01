import socket
import threading
import json
import time
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime

class StorageNode:
    def __init__(self, network_host='localhost', network_port=9000, 
                 node_port=None, storage_path=None, capacity_gb=5):
        self.network_host = network_host
        self.network_port = network_port
        self.node_id = str(uuid.uuid4())[:8]
        self.node_port = node_port or (10000 + int(time.time() * 1000) % 10000)
        self.storage_capacity = capacity_gb * 1024 * 1024 * 1024
        self.used_storage = 0
        
        # Setup storage directory
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path(f"./node_storage/{self.node_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.running = False
        self.files = {}  # file_id -> file_info
        self._calculate_used_storage()
        
    def _calculate_used_storage(self):
        """Calculate currently used storage"""
        total = 0
        for file_path in self.storage_path.rglob('*'):
            if file_path.is_file():
                total += file_path.stat().st_size
        self.used_storage = total
    
    def start(self):
        """Start the storage node"""
        self.running = True
        
        # Register with network
        if not self._register_with_network():
            print(f"❌ Failed to register with network server")
            return
        
        # Start node server
        threading.Thread(target=self._start_node_server, daemon=True).start()
        
        # Start heartbeat
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        
        print(f"\n{'='*60}")
        print(f"Storage Node Running")
        print(f"{'='*60}")
        print(f"Node ID: {self.node_id}")
        print(f"Port: {self.node_port}")
        print(f"Storage: {self.used_storage/(1024**3):.2f}/{self.storage_capacity/(1024**3):.2f} GB")
        print(f"{'='*60}\n")
        
        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def _register_with_network(self):
        """Register this node with the network server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.network_host, self.network_port))
            
            # Get local IP
            local_ip = socket.gethostbyname(socket.gethostname())
            
            message = {
                'type': 'register_node',
                'node_id': self.node_id,
                'ip': local_ip,
                'port': self.node_port,
                'storage_capacity': self.storage_capacity,
                'used_storage': self.used_storage
            }
            
            sock.send(json.dumps(message).encode('utf-8'))
            response = json.loads(sock.recv(4096).decode('utf-8'))
            sock.close()
            
            return response.get('status') == 'success'
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def _heartbeat_loop(self):
        """Send periodic heartbeats to network server"""
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.network_host, self.network_port))
                
                message = {
                    'type': 'heartbeat',
                    'node_id': self.node_id,
                    'used_storage': self.used_storage
                }
                
                sock.send(json.dumps(message).encode('utf-8'))
                sock.recv(1024)
                sock.close()
            except Exception as e:
                print(f"⚠️  Heartbeat failed: {e}")
            
            time.sleep(10)
    
    def _start_node_server(self):
        """Start server to handle file operations"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', self.node_port))
        server_socket.listen(10)
        
        while self.running:
            try:
                client_socket, address = server_socket.accept()
                threading.Thread(
                    target=self._handle_request,
                    args=(client_socket,),
                    daemon=True
                ).start()
            except Exception as e:
                if self.running:
                    print(f"❌ Server error: {e}")
    
    def _handle_request(self, client_socket):
        """Handle incoming requests"""
        try:
            # Receive request
            data = b''
            while True:
                chunk = client_socket.recv(4096)
                data += chunk
                if len(chunk) < 4096:
                    break
            
            request = json.loads(data.decode('utf-8'))
            request_type = request.get('type')
            
            if request_type == 'upload':
                response = self._handle_upload(request, client_socket)
            elif request_type == 'download':
                response = self._handle_download(request, client_socket)
            elif request_type == 'delete':
                response = self._handle_delete(request)
            else:
                response = {'status': 'error', 'message': 'Unknown request'}
            
            if request_type != 'download':  # Download sends file directly
                client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"❌ Request handling error: {e}")
            client_socket.send(json.dumps({
                'status': 'error',
                'message': str(e)
            }).encode('utf-8'))
        finally:
            client_socket.close()
    
    def _handle_upload(self, request, client_socket):
        """Handle file upload"""
        file_id = request.get('file_id')
        file_name = request.get('file_name')
        file_size = request.get('file_size')
        
        # Check storage
        if self.used_storage + file_size > self.storage_capacity:
            return {'status': 'error', 'message': 'Insufficient storage'}
        
        # Prepare to receive file
        file_path = self.storage_path / file_id
        
        print(f"📥 Receiving: {file_name} ({file_size/(1024**2):.2f} MB)")
        
        # Send ready signal
        client_socket.send(b'READY')
        
        # Receive file data
        received = 0
        with open(file_path, 'wb') as f:
            while received < file_size:
                chunk_size = min(8192, file_size - received)
                chunk = client_socket.recv(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
        
        # Update storage
        self.used_storage += file_size
        self.files[file_id] = {
            'file_id': file_id,
            'file_name': file_name,
            'file_size': file_size,
            'upload_time': time.time()
        }
        
        print(f"✅ Uploaded: {file_name} | Storage: {self.used_storage/(1024**3):.2f}/{self.storage_capacity/(1024**3):.2f} GB\n")
        
        return {'status': 'success', 'bytes_received': received}
    
    def _handle_download(self, request, client_socket):
        """Handle file download"""
        file_id = request.get('file_id')
        file_path = self.storage_path / file_id
        
        if not file_path.exists():
            client_socket.send(json.dumps({
                'status': 'error',
                'message': 'File not found'
            }).encode('utf-8'))
            return
        
        file_size = file_path.stat().st_size
        file_name = self.files.get(file_id, {}).get('file_name', 'unknown')
        
        print(f"📤 Sending: {file_name} ({file_size/(1024**2):.2f} MB)")
        
        # Send file info
        client_socket.send(json.dumps({
            'status': 'success',
            'file_size': file_size
        }).encode('utf-8'))
        
        # Wait for client ready
        client_socket.recv(1024)
        
        # Send file data
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                client_socket.send(chunk)
        
        print(f"✅ Sent: {file_name}\n")
    
    def _handle_delete(self, request):
        """Handle file deletion"""
        file_id = request.get('file_id')
        file_path = self.storage_path / file_id
        
        if file_path.exists():
            file_size = file_path.stat().st_size
            file_path.unlink()
            self.used_storage -= file_size
            
            if file_id in self.files:
                file_name = self.files[file_id]['file_name']
                del self.files[file_id]
                print(f"🗑️  Deleted: {file_name}\n")
            
            return {'status': 'success'}
        
        return {'status': 'error', 'message': 'File not found'}
    
    def stop(self):
        """Stop the node"""
        print(f"\n🛑 Stopping node {self.node_id}...")
        self.running = False

if __name__ == '__main__':
    # Parse command line arguments
    network_host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    capacity_gb = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    node = StorageNode(
        network_host=network_host,
        network_port=9000,
        capacity_gb=capacity_gb
    )
    
    try:
        node.start()
    except KeyboardInterrupt:
        node.stop()