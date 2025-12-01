import socket
import threading
import json
import time
from datetime import datetime
from typing import Dict, List, Set
import uuid

class NetworkServer:
    def __init__(self, host='0.0.0.0', port=9000):
        self.host = host
        self.port = port
        self.nodes: Dict[str, dict] = {}  # node_id -> node_info
        self.file_registry: Dict[str, List[str]] = {}  # file_id -> [node_ids]
        self.user_files: Dict[str, List[dict]] = {}  # user_id -> [file_info]
        self.active_transfers: Dict[str, dict] = {}
        self.lock = threading.Lock()
        self.running = False
        
    def start(self):
        """Start the network server"""
        self.running = True
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(50)
        
        print(f"╔{'═'*60}╗")
        print(f"║{'Network Server Started':^60}║")
        print(f"╠{'═'*60}╣")
        print(f"║  Host: {self.host:<50} ║")
        print(f"║  Port: {self.port:<50} ║")
        print(f"║  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<50} ║")
        print(f"╚{'═'*60}╝\n")
        
        # Start health check thread
        threading.Thread(target=self._health_check_loop, daemon=True).start()
        
        try:
            while self.running:
                try:
                    client_socket, address = server_socket.accept()
                    threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    ).start()
                except Exception as e:
                    if self.running:
                        print(f"❌ Error accepting connection: {e}")
        finally:
            server_socket.close()
    
    def _handle_client(self, client_socket, address):
        """Handle client connection"""
        try:
            while self.running:
                data = client_socket.recv(8192)
                if not data:
                    break
                    
                message = json.loads(data.decode('utf-8'))
                response = self._process_message(message)
                
                client_socket.send(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"⚠️  Connection error from {address}: {e}")
        finally:
            client_socket.close()
    
    def _process_message(self, message: dict) -> dict:
        """Process incoming message"""
        msg_type = message.get('type')
        
        if msg_type == 'register_node':
            return self._register_node(message)
        elif msg_type == 'heartbeat':
            return self._handle_heartbeat(message)
        elif msg_type == 'get_available_nodes':
            return self._get_available_nodes(message)
        elif msg_type == 'register_file':
            return self._register_file(message)
        elif msg_type == 'get_file_locations':
            return self._get_file_locations(message)
        elif msg_type == 'upload_request':
            return self._handle_upload_request(message)
        elif msg_type == 'download_request':
            return self._handle_download_request(message)
        elif msg_type == 'get_user_files':
            return self._get_user_files(message)
        elif msg_type == 'delete_file':
            return self._delete_file(message)
        else:
            return {'status': 'error', 'message': 'Unknown message type'}
    
    def _register_node(self, message: dict) -> dict:
        """Register a new storage node"""
        with self.lock:
            node_id = message.get('node_id', str(uuid.uuid4()))
            node_info = {
                'node_id': node_id,
                'ip': message.get('ip'),
                'port': message.get('port'),
                'storage_capacity': message.get('storage_capacity', 0),
                'used_storage': message.get('used_storage', 0),
                'last_heartbeat': time.time(),
                'status': 'online'
            }
            
            self.nodes[node_id] = node_info
            
            print(f"✅ Node registered: {node_id}")
            print(f"   └─ IP: {node_info['ip']}:{node_info['port']}")
            print(f"   └─ Capacity: {node_info['storage_capacity'] / (1024**3):.2f} GB\n")
            
            return {'status': 'success', 'node_id': node_id, 'node_info': node_info}
    
    def _handle_heartbeat(self, message: dict) -> dict:
        """Handle node heartbeat"""
        node_id = message.get('node_id')
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]['last_heartbeat'] = time.time()
                self.nodes[node_id]['used_storage'] = message.get('used_storage', 0)
                self.nodes[node_id]['status'] = 'online'
                return {'status': 'success'}
        return {'status': 'error', 'message': 'Node not found'}
    
    def _get_available_nodes(self, message: dict) -> dict:
        """Get list of available nodes"""
        with self.lock:
            available_nodes = [
                node for node in self.nodes.values()
                if node['status'] == 'online'
            ]
            return {'status': 'success', 'nodes': available_nodes}
    
    def _register_file(self, message: dict) -> dict:
        """Register a file in the network"""
        with self.lock:
            file_id = message.get('file_id')
            node_ids = message.get('node_ids', [])
            user_id = message.get('user_id')
            file_info = message.get('file_info')
            
            # Update file registry
            if file_id not in self.file_registry:
                self.file_registry[file_id] = []
            self.file_registry[file_id].extend(node_ids)
            
            # Update user files
            if user_id not in self.user_files:
                self.user_files[user_id] = []
            self.user_files[user_id].append(file_info)
            
            print(f"📄 File registered: {file_info['file_name']}")
            print(f"   └─ Size: {file_info['file_size'] / (1024**2):.2f} MB")
            print(f"   └─ Nodes: {', '.join(node_ids)}\n")
            
            return {'status': 'success'}
    
    def _get_file_locations(self, message: dict) -> dict:
        """Get node locations for a file"""
        file_id = message.get('file_id')
        with self.lock:
            node_ids = self.file_registry.get(file_id, [])
            nodes = [self.nodes[nid] for nid in node_ids if nid in self.nodes and self.nodes[nid]['status'] == 'online']
            return {'status': 'success', 'nodes': nodes}
    
    def _handle_upload_request(self, message: dict) -> dict:
        """Handle upload request - select best node"""
        file_size = message.get('file_size')
        with self.lock:
            # Find node with enough space
            suitable_nodes = [
                node for node in self.nodes.values()
                if node['status'] == 'online' and 
                (node['storage_capacity'] - node['used_storage']) >= file_size
            ]
            
            if not suitable_nodes:
                return {'status': 'error', 'message': 'No available storage nodes'}
            
            # Select node with most free space
            best_node = max(suitable_nodes, key=lambda n: n['storage_capacity'] - n['used_storage'])
            
            print(f"📤 Upload request assigned to: {best_node['node_id']}\n")
            
            return {'status': 'success', 'node': best_node}
    
    def _handle_download_request(self, message: dict) -> dict:
        """Handle download request"""
        file_id = message.get('file_id')
        return self._get_file_locations({'file_id': file_id})
    
    def _get_user_files(self, message: dict) -> dict:
        """Get all files for a user"""
        user_id = message.get('user_id')
        with self.lock:
            files = self.user_files.get(user_id, [])
            return {'status': 'success', 'files': files}
    
    def _delete_file(self, message: dict) -> dict:
        """Delete a file from the network"""
        file_id = message.get('file_id')
        user_id = message.get('user_id')
        
        with self.lock:
            # Remove from registry
            if file_id in self.file_registry:
                del self.file_registry[file_id]
            
            # Remove from user files
            if user_id in self.user_files:
                self.user_files[user_id] = [
                    f for f in self.user_files[user_id] 
                    if f['file_id'] != file_id
                ]
            
            print(f"🗑️  File deleted: {file_id}\n")
            
            return {'status': 'success'}
    
    def _health_check_loop(self):
        """Periodically check node health"""
        while self.running:
            time.sleep(10)
            current_time = time.time()
            
            with self.lock:
                for node_id, node_info in self.nodes.items():
                    if current_time - node_info['last_heartbeat'] > 30:
                        if node_info['status'] == 'online':
                            node_info['status'] = 'offline'
                            print(f"⚠️  Node offline: {node_id}\n")

if __name__ == '__main__':
    server = NetworkServer(host='0.0.0.0', port=9000)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down network server...")
        server.running = False