import socket
import pickle
import threading
import time

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(2)  # Chỉ chấp nhận 2 kết nối (2 người chơi)
        print(f"Server đang chạy và lắng nghe trên {host}:{port}")
        
        # Trạng thái game
        self.game_state = {
            "player1": {"x": 100, "y": 100, "score": 0},
            "player2": {"x": 400, "y": 400, "score": 0},
            "game_active": False
        }
        
        self.clients = []
        self.player_ids = {}  # Ánh xạ socket đến ID người chơi
        
    def handle_client(self, client, player_id):
        """Xử lý kết nối từ một client cụ thể"""
        try:
            while True:
                # Nhận dữ liệu từ client
                data = client.recv(4096)
                if not data:
                    break
                
                # Giải mã dữ liệu nhận được
                client_data = pickle.loads(data)
                
                # Cập nhật trạng thái game dựa trên dữ liệu nhận được
                if "position" in client_data:
                    self.game_state[player_id]["x"] = client_data["position"]["x"]
                    self.game_state[player_id]["y"] = client_data["position"]["y"]
                
                if "action" in client_data:
                    # Xử lý các hành động của người chơi
                    # Ví dụ: nhảy, đánh, v.v.
                    pass
                
                # Gửi trạng thái game cập nhật cho tất cả client
                self.broadcast_game_state()
                
        except Exception as e:
            print(f"Lỗi xử lý client {player_id}: {e}")
        finally:
            # Dọn dẹp khi client ngắt kết nối
            print(f"{player_id} đã ngắt kết nối")
            if client in self.clients:
                self.clients.remove(client)
            if client in self.player_ids:
                del self.player_ids[client]
            client.close()
            
            # Cập nhật trạng thái game
            if player_id in self.game_state:
                self.game_state["game_active"] = False
                
    def broadcast_game_state(self):
        """Gửi trạng thái game hiện tại cho tất cả client"""
        serialized_state = pickle.dumps(self.game_state)
        for client in self.clients:
            try:
                client.send(serialized_state)
            except:
                # Nếu không gửi được, có thể client đã ngắt kết nối
                pass
                
    def run(self):
        """Chạy server và chấp nhận kết nối"""
        try:
            player_count = 0
            while True:
                client, addr = self.server.accept()
                print(f"Kết nối từ {addr}")
                
                if player_count < 2:
                    player_count += 1
                    player_id = f"player{player_count}"
                    
                    # Lưu thông tin client
                    self.clients.append(client)
                    self.player_ids[client] = player_id
                    
                    # Gửi ID cho client
                    client.send(pickle.dumps({"player_id": player_id}))
                    
                    # Tạo thread xử lý client này
                    client_thread = threading.Thread(target=self.handle_client, args=(client, player_id))
                    client_thread.daemon = True
                    client_thread.start()
                    
                    # Nếu có đủ 2 người chơi, bắt đầu game
                    if player_count == 2:
                        self.game_state["game_active"] = True
                        time.sleep(1)  # Chờ các client sẵn sàng
                        self.broadcast_game_state()
                else:
                    # Từ chối kết nối nếu đã đủ người chơi
                    client.send(pickle.dumps({"error": "Phòng đã đầy"}))
                    client.close()
                    
        except KeyboardInterrupt:
            print("Server đang dừng...")
        except Exception as e:
            print(f"Lỗi server: {e}")
        finally:
            self.server.close()

if __name__ == "__main__":
    server = GameServer()
    server.run()