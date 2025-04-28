import socket
import pickle
import threading
import pygame
import sys

class GameClient:
    def __init__(self, host='localhost', port=5555):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = host
        self.port = port
        self.addr = (self.server, self.port)
        self.player_id = None
        self.game_state = None
        self.running = True
        
        # Khởi tạo pygame
        pygame.init()
        self.width, self.height = 800, 600
        self.win = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Brawler Game")
        self.clock = pygame.time.Clock()
        
        # Màu sắc
        self.WHITE = (255, 255, 255)
        self.RED = (255, 0, 0)
        self.BLUE = (0, 0, 255)
        
    def connect(self):
        """Kết nối đến server"""
        try:
            self.client.connect(self.addr)
            print(f"Đã kết nối đến server tại {self.addr}")
            
            # Nhận ID người chơi từ server
            data = self.client.recv(4096)
            response = pickle.loads(data)
            
            if "error" in response:
                print(f"Lỗi: {response['error']}")
                return False
            
            self.player_id = response["player_id"]
            print(f"Bạn là {self.player_id}")
            
            # Khởi động thread nhận dữ liệu từ server
            receive_thread = threading.Thread(target=self.receive_data)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
            
        except Exception as e:
            print(f"Lỗi kết nối: {e}")
            return False
            
    def receive_data(self):
        """Nhận dữ liệu từ server liên tục"""
        while self.running:
            try:
                data = self.client.recv(4096)
                if not data:
                    break
                    
                self.game_state = pickle.loads(data)
                
            except Exception as e:
                print(f"Lỗi nhận dữ liệu: {e}")
                break
                
        print("Ngắt kết nối từ server")
        self.running = False
        
    def send_data(self, data):
        """Gửi dữ liệu đến server"""
        try:
            self.client.send(pickle.dumps(data))
        except Exception as e:
            print(f"Lỗi gửi dữ liệu: {e}")
            self.running = False
            
    def process_input(self):
        """Xử lý đầu vào từ người chơi"""
        keys = pygame.key.get_pressed()
        
        # Vị trí hiện tại
        if self.game_state and self.player_id in self.game_state:
            current_x = self.game_state[self.player_id]["x"]
            current_y = self.game_state[self.player_id]["y"]
            
            # Chuyển động
            move_x, move_y = 0, 0
            speed = 5
            
            if keys[pygame.K_LEFT]:
                move_x = -speed
            if keys[pygame.K_RIGHT]:
                move_x = speed
            if keys[pygame.K_UP]:
                move_y = -speed
            if keys[pygame.K_DOWN]:
                move_y = speed
                
            # Chỉ gửi dữ liệu nếu có sự thay đổi
            if move_x != 0 or move_y != 0:
                new_x = current_x + move_x
                new_y = current_y + move_y
                
                # Giới hạn trong màn hình
                new_x = max(0, min(self.width - 50, new_x))
                new_y = max(0, min(self.height - 50, new_y))
                
                # Gửi vị trí mới đến server
                self.send_data({
                    "position": {"x": new_x, "y": new_y}
                })
                
            # Xử lý nút tấn công
            if keys[pygame.K_SPACE]:
                self.send_data({
                    "action": "attack"
                })
                
    def render(self):
        """Hiển thị trạng thái game"""
        self.win.fill((0, 0, 0))  # Xóa màn hình
        
        if self.game_state:
            # Hiển thị thông báo nếu game chưa bắt đầu
            if not self.game_state["game_active"]:
                font = pygame.font.SysFont(None, 36)
                text = font.render("Đang chờ người chơi khác...", True, self.WHITE)
                self.win.blit(text, (self.width//2 - text.get_width()//2, self.height//2))
            else:
                # Vẽ người chơi 1
                if "player1" in self.game_state:
                    pygame.draw.rect(self.win, self.RED, 
                                    (self.game_state["player1"]["x"], 
                                     self.game_state["player1"]["y"], 50, 50))
                
                # Vẽ người chơi 2
                if "player2" in self.game_state:
                    pygame.draw.rect(self.win, self.BLUE, 
                                    (self.game_state["player2"]["x"], 
                                     self.game_state["player2"]["y"], 50, 50))
                
                # Hiển thị điểm số
                font = pygame.font.SysFont(None, 24)
                score1 = font.render(f"P1: {self.game_state['player1']['score']}", True, self.WHITE)
                score2 = font.render(f"P2: {self.game_state['player2']['score']}", True, self.WHITE)
                self.win.blit(score1, (10, 10))
                self.win.blit(score2, (10, 40))
                
                # Hiển thị thông tin người chơi
                player_info = font.render(f"Bạn là: {self.player_id}", True, self.WHITE)
                self.win.blit(player_info, (self.width - player_info.get_width() - 10, 10))
        
        pygame.display.update()
        
    def run(self):
        """Vòng lặp chính của game"""
        if not self.connect():
            return
            
        # Vòng lặp game
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
            self.process_input()
            self.render()
            self.clock.tick(60)  # 60 FPS
            
        # Dọn dẹp khi kết thúc
        pygame.quit()
        self.client.close()

if __name__ == "__main__":
    # Lấy địa chỉ IP server từ tham số dòng lệnh hoặc sử dụng localhost
    server_ip = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    client = GameClient(host=server_ip)
    client.run()