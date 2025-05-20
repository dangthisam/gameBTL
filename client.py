import socket
import pickle
import threading
import pygame
from pygame import mixer
import sys
import time

from fighter import Fighter

class GameClient:
    def __init__(self, host='localhost', port=5555):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = host # Server address
        self.port = port # Server port
        self.addr = (self.server, self.port) # Server address tuple
        self.player_id = None # Player ID (player1 or player2)
        self.game_state = None # Game state received from server
        self.running = True  # Main game loop flag
        self.connection_established = False  # Connection status flag
        self.connection_error = None # Connection error message
        self.connection_retry_count = 0 # Number of connection attempts
        self.max_retries = 3  # Maximum number of connection attempts

        ## Chat variables
        self.chat_messages = []  # Danh sách tin nhắn nhận từ server
        self.chat_input = ""  # lưu trữ tin nhắn đang nhập
        self.chat_active = False  # Trạng thái nhập tin nhắn
        self.max_chat_messages = 1 # Số tin nhắn tối đa hiển thị trên màn hình

            ## Chat message display control
        self.show_chat_messages = False      # Control chat messages visibility
        self.chat_display_timer = 0          # Timer for chat messages display
        self.CHAT_DISPLAY_DURATION = 2000 # Duration to display chat messages (in milliseconds)
        # Track previous round_over state to detect new rounds
        self.was_round_over = False
        
    
        # Initialize pygame and mixer
        mixer.init()
        pygame.init()
        
        # Game window setup
        self.SCREEN_WIDTH = 1300
        self.SCREEN_HEIGHT = 800
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Brawler Game - Network Edition")
        self.clock = pygame.time.Clock()
        self.FPS = 60
        
        # Colors
        self.RED = (255, 0, 0)
        self.YELLOW = (255, 255, 0)
        self.WHITE = (255, 255, 255)
        self.BLUE = (0, 0, 255)
        self.BLACK = (0, 0, 0)
        self.GREEN = (0, 255, 0)
        self.ORANGE = (255, 165, 0)
        self.PINK = (255, 192, 203)
        self.GRAY=(128,128,128)
        self.LIGHT_GRAY=(192,192,192)
        
        
        # Game variables
        self.intro_count = 5 # Countdown for intro
        self.last_count_update = pygame.time.get_ticks() # Last time count was updated
        self.round_over = False # Round over flag
        self.ROUND_OVER_COOLDOWN = 2000 # Cooldown time for round over state
        self.game_over = False # Game over flag
        self.WIN_SCORE = 5 # Score needed to win the game
        self.winner = 0 # Winner ID (1 or 2)
        self.show_controls = True
        self.character_selection = True  # Cờ để hiển thị màn hình chọn nhân vật sau màn hình điều khiển.
        self.player_selection = [0, 0]  # Lưu chỉ số nhân vật được chọn cho mỗi người chơi (0 = Warrior, 1 = Wizard, v.v.).
        
        # Fighter variables
        self.WARRIOR_SIZE = 162
        self.WARRIOR_SCALE = 4
        self.WARRIOR_OFFSET = [72, 56]
        self.WARRIOR_DATA = [self.WARRIOR_SIZE, self.WARRIOR_SCALE, self.WARRIOR_OFFSET]

        self.WIZARD_SIZE = 250
        self.WIZARD_SCALE = 3
        self.WIZARD_OFFSET = [112, 107]
        self.WIZARD_DATA = [self.WIZARD_SIZE, self.WIZARD_SCALE, self.WIZARD_OFFSET]
        
        self.HUNTRESS_SIZE = 250
        self.HUNTRESS_SCALE = 3
        self.HUNTRESS_OFFSET = [112, 107]
        self.HUNTRESS_DATA = [self.HUNTRESS_SIZE, self.HUNTRESS_SCALE, self.HUNTRESS_OFFSET]

        # Kích thước và thông số cho Medieval Warrior Pack 3
        self.MEDIEVALWARRIORPACK3_SIZE = 200
        self.MEDIEVALWARRIORPACK3_SCALE = 3
        self.MEDIEVALWARRIORPACK3_OFFSET = [86, 68]
        self.MEDIEVALWARRIORPACK3_DATA = [self.MEDIEVALWARRIORPACK3_SIZE, self.MEDIEVALWARRIORPACK3_SCALE, self.MEDIEVALWARRIORPACK3_OFFSET]
        # Load resources
     
        self.fighter_1_initial_x = 0 + 10  # Position fighter 1 at the left edge
        self.fighter_1_initial_y = self.SCREEN_HEIGHT // 2 + 50  # Adjusted to be relative to screen height
        self.fighter_2_initial_x = self.SCREEN_WIDTH - 100  # Position fighter 2 closer to the right edge
        self.fighter_2_initial_y = self.SCREEN_HEIGHT // 2 + 50  # Adjusted to be relative to screen height
        self.fighter_1 = None
        self.fighter_2 = None
        # Initialize CHARACTER_DATA
        self.CHARACTER_DATA = [
            {"name": "WARRIOR", "data": [162, 4, [72, 56]], "sheet": None, "steps": [10, 8, 1, 7, 7, 3, 7], "sound": None, "color": self.RED},
            {"name": "WIZARD", "data": [250, 3, [112, 107]], "sheet": None, "steps": [8, 8, 1, 8, 8, 3, 7], "sound": None, "color": self.BLUE},
            {"name": "HUNTRESS", "data": [250, 3, [112, 107]], "sheet": None, "steps": [8, 8, 2, 5, 5, 3, 7], "sound": None, "color": self.GREEN},
            {"name": "MEDIEVAL WARRIOR", "data": [200, 3, [86, 68]], "sheet": None, "steps": [10, 6, 2, 4, 4, 3, 9], "sound": None, "color": self.ORANGE}
        ]
        self.load_resources() # Load game resources
        # Create fighters
    def create_fighters(self):
        """Tạo Fighter dựa trên lựa chọn nhân vật"""
        p1_char = self.CHARACTER_DATA[self.player_selection[0]]
        p2_char = self.CHARACTER_DATA[self.player_selection[1]]
        self.fighter_1 = Fighter(1, self.fighter_1_initial_x, self.fighter_1_initial_y, False,
                                p1_char["data"], p1_char["sheet"], p1_char["steps"], p1_char["sound"])
        self.fighter_2 = Fighter(2, self.fighter_2_initial_x, self.fighter_2_initial_y, True,
                                p2_char["data"], p2_char["sheet"], p2_char["steps"], p2_char["sound"])
        
        # Store initial positions for resetting
        

        # Network update rate (to prevent flooding the server)
        self.last_update_time = 0
        self.update_interval = 1000 / 30  # 30 updates per second
        
    def load_resources(self):
        """Load game resources"""
        try:
            # Load music and sounds
            pygame.mixer.music.load("assets/audio/ok.mp3") # Load background music
            pygame.mixer.music.set_volume(1) # Set volume
            pygame.mixer.music.play(-1, 0.0, 5000) # Loop music indefinitely
            self.CHARACTER_DATA[0]["sheet"] = pygame.image.load("assets/images/warrior/Sprites/warrior.png").convert_alpha()
            self.CHARACTER_DATA[0]["sound"] = pygame.mixer.Sound("assets/audio/sword.wav")
            self.CHARACTER_DATA[1]["sheet"] = pygame.image.load("assets/images/wizard/Sprites/wizard.png").convert_alpha()
            self.CHARACTER_DATA[1]["sound"] = pygame.mixer.Sound("assets/audio/magic.wav")
            self.CHARACTER_DATA[2]["sheet"] = pygame.image.load("assets/images/Huntress/Sprites/Huntress.png").convert_alpha()
            self.CHARACTER_DATA[2]["sound"] = pygame.mixer.Sound("assets/audio/sword.wav")
            self.CHARACTER_DATA[3]["sheet"] = pygame.image.load("assets/images/MedievalWarriorPack3/Sprites/MedievalWarriorPack3.png").convert_alpha()
            self.CHARACTER_DATA[3]["sound"] = pygame.mixer.Sound("assets/audio/sword.wav")

            
            # Load background image
            self.bg_image = pygame.image.load("assets/images/background/background.jpg").convert_alpha()
            
            # Load spritesheets
            self.warrior_sheet = pygame.image.load("assets/images/warrior/Sprites/warrior.png").convert_alpha()
            self.wizard_sheet = pygame.image.load("assets/images/wizard/Sprites/wizard.png").convert_alpha()
            

            self.huntress_sheet = pygame.image.load( "assets/images/Huntress/Sprites/Huntress.png").convert_alpha()
                                                
            self.medievalwarriorpack3_sheet = pygame.image.load(  "assets/images/MedievalWarriorPack3/Sprites/MedievalWarriorPack3.png").convert_alpha()
  
            
            # Load victory image
            self.victory_img = pygame.image.load("assets/images/icons/victory.png").convert_alpha()
            
            # Define fonts
            self.count_font = pygame.font.Font("assets/fonts/transMutation.ttf", 80)
            self.score_font = pygame.font.Font("assets/fonts/transMutation.ttf", 30)
            self.game_over_font = pygame.font.Font("assets/fonts/transMutation.ttf", 50)
            self.controls_font = pygame.font.Font("assets/fonts/transMutation.ttf", 25)
            self.title_font = pygame.font.Font("assets/fonts/transMutation.ttf", 40)
        except Exception as e:
            print(f"Error loading resources: {e}")
            pygame.quit()
            sys.exit()
    
    def reset_fighter_state(self, fighter, initial_x, initial_y):
        """Reset a fighter to initial state for a new round"""
        fighter.rect.x = initial_x
        fighter.rect.y = initial_y
        fighter.health = 100
        fighter.alive = True
        fighter.attacking = False
        fighter.attack_type = 0
        fighter.attack_cooldown = 0
        fighter.hit = False
        fighter.action = 0  # Idle action
        fighter.frame_index = 0
        fighter.velocity_y = 0
        fighter.jump = False
        fighter.in_air = False
        fighter.attack_sound_played = False
        
        # Ensure fighter stops attacking
        fighter.update_action(0)  # Set to idle
    
    def connect(self):
        """Connect to the server with retry mechanism"""
        while self.connection_retry_count < self.max_retries and not self.connection_established:
            try:
                print(f"Attempting to connect to server at {self.addr} (Attempt {self.connection_retry_count + 1}/{self.max_retries})")
                
                # Set socket timeout for connection
                self.client.settimeout(5)
                
                # The key fix: Make sure we're using a proper IP address for the server
                # if not on the same machine
                self.client.connect(self.addr)
                
                # Reset timeout to None (blocking mode) for normal operation
                self.client.settimeout(None)
                
                print(f"Connected to server at {self.addr}")
                
                # Receive player ID from server
                data = self.client.recv(4096)
                if not data:
                    raise Exception("No data received from server")
                    
                response = pickle.loads(data)  # Unpickle the response
                
                if "error" in response:
                    raise Exception(f"Server error: {response['error']}")
                
                self.player_id = response["player_id"]
                print(f"You are {self.player_id}")
                
                # Send initial confirmation to server
                self.send_data({"player_id": self.player_id, "status": "connected"})
                
                # Start receiving data from server
                self.connection_established = True
                receive_thread = threading.Thread(target=self.receive_data)
                receive_thread.daemon = True
                receive_thread.start()
                
                # Connection successful
                return True
                
            except Exception as e:
                self.connection_error = str(e)
                print(f"Connection error: {e}")
                self.connection_retry_count += 1
                
                # Close socket and create a new one for retry
                try:
                    self.client.close()
                except:
                    pass
                    
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                time.sleep(1)  # Wait before retrying connection
        
        # If we've exhausted our retries
        if not self.connection_established:
            print("Failed to connect to server after multiple attempts")
            return False
    def receive_data(self):
        """Continuously receive data from server"""
        self.client.settimeout(5)  # Set timeout to detect disconnection

        while self.running:  # Keep receiving data until the game is over or connection is lost
            try:
                data = self.client.recv(4096)  # Receive data from server
                if not data:
                    print("Server disconnected (no data)")
                    break

                self.game_state = pickle.loads(data)  # Unpickle the received data
                if self.game_state is None:
                    print("Received None data from server")
                    break

                # Update local game state based on server data
                if self.game_state and "game_active" in self.game_state:
                    # Sync player selection with server's state
                    if "player_selection" in self.game_state:
                        old_selection = self.player_selection.copy()
                        self.player_selection = self.game_state["player_selection"]
                        if old_selection != self.player_selection:
                            print(f"Player selection updated: {old_selection} -> {self.player_selection}")

                        # Create fighters if they don't exist yet
                        if self.fighter_1 is None and self.fighter_2 is None and self.game_state.get("game_active", False):
                            self.create_fighters()

                    # Update chat messages
                    if "chat_messages" in self.game_state:
                        if self.chat_messages != self.game_state["chat_messages"]:
                            self.chat_messages = self.game_state["chat_messages"]
                            self.show_chat_messages = True
                            self.chat_display_timer = pygame.time.get_ticks()

                    # Handle round state changes
                    new_round_over = self.game_state["round_over"]
                    if self.was_round_over and not new_round_over:
                        print("New round starting - resetting local fighter state")
                        if self.player_id == "player1":
                            self.reset_fighter_state(self.fighter_1, self.fighter_1_initial_x, self.fighter_1_initial_y)
                        elif self.player_id == "player2":
                            self.reset_fighter_state(self.fighter_2, self.fighter_2_initial_x, self.fighter_2_initial_y)

                    self.was_round_over = new_round_over
                    self.round_over = new_round_over
                    self.game_over = self.game_state["game_over"]
                    self.winner = self.game_state["winner"]

                    # Update fighter states
                    if self.game_state["game_active"] and self.fighter_1 and self.fighter_2:
                        if self.player_id == "player1":
                            self.fighter_1.health = self.game_state["player1"]["health"]
                            self.fighter_1.hit = self.game_state["player1"]["hit"]

                            if "player2" in self.game_state:
                                self.update_fighter_state(self.fighter_2, self.game_state["player2"])
                        elif self.player_id == "player2":
                            self.fighter_2.health = self.game_state["player2"]["health"]
                            self.fighter_2.hit = self.game_state["player2"]["hit"]

                            if "player1" in self.game_state:
                                self.update_fighter_state(self.fighter_1, self.game_state["player1"])

            except socket.timeout:
                # Just a timeout, continue the loop
                continue
            except (ConnectionResetError, ConnectionAbortedError) as e:
                print(f"Connection lost: {e}")
                break
            except Exception as e:
                print(f"Error receiving data: {e}")
                # Try to continue instead of breaking immediately
                if not self.running:
                    break
                time.sleep(0.5)  # Brief pause before trying again
                continue
        
        print("Disconnected from server")
        self.connection_established = False
        self.running = False

    def update_fighter_state(self, fighter, state):
        """Update a fighter's state based on server data"""
        fighter.rect.x = state["x"]
        fighter.rect.y = state["y"]
        fighter.health = state["health"]
        fighter.action = state["action"]
        fighter.frame_index = state["frame_index"]
        fighter.flip = state["flip"]
        fighter.attacking = state["attacking"]
        fighter.hit = state["hit"]
        
    def send_data(self, data):
        """Send data to server with error handling"""
        """Send data to server with error handling"""
        if not self.connection_established:
            return
            
        try:
            serialized_data = pickle.dumps(data)
            self.client.send(serialized_data)
        except ConnectionResetError:
            print("Connection reset by server while sending data")
            self.connection_established = False
            self.running = False
        except Exception as e:
            print(f"Error sending data: {e}")
            # Don't immediately set running to False
            # This allows the receive thread to handle reconnection if needed
            self.connection_established = False
    
    def draw_text(self, text, font, text_col, x, y):
        """Draw text on screen"""
        img = font.render(text, True, text_col) # Render text
        text_rect = img.get_rect(center=(x, y)) # Get text rectangle
        self.screen.blit(img, text_rect) # Blit text on screen

    def draw_character_selection(self):
            """Draw character selection screen using self.player_selection"""
            s = pygame.Surface((self.SCREEN_WIDTH,self.SCREEN_HEIGHT))
            s.set_alpha(220)
            s.fill(self.BLACK)
            self.screen.blit(s, (0, 0))

            # tiêu đề
            self.draw_text("CHARACTER SELECTION", self.title_font, self.YELLOW, self.SCREEN_WIDTH // 2, 50)

            # Các ô nhân vật
            character_width = 250 #kích thuoc
            character_height = 350
            spacing = 40 # khoảng cách các ô
            # Tọa độ x bắt đầu, căn giữa bằng cách trừ tổng chiều rộng (4 ô + 3 khoảng cách) khỏi chiều rộng màn hình.
            start_x = (self.SCREEN_WIDTH - (character_width * 4 + spacing * 3)) // 2

            for i in range(4):
                # lấy màu từ character_data
                # Lấy màu và spritesheet từ CHARACTER_DATA
                box_color = self.CHARACTER_DATA[i]["color"]
                sprite_sheet = self.CHARACTER_DATA[i]["sheet"]
                # .rect vẽ khung
                # Add a subtle shadow effect for the character box
                shadow_rect = pygame.Rect(start_x + i * (character_width + spacing) + 5, 125, character_width, character_height)
                pygame.draw.rect(self.screen, (50, 50, 50), shadow_rect, 0)

                # Draw the main character box with a gradient effect
                rect = pygame.Rect(start_x + i * (character_width + spacing), 120, character_width, character_height)
                gradient_surface = pygame.Surface((character_width, character_height), pygame.SRCALPHA)
                for y in range(character_height):
                    alpha = int(255 * (1 - y / character_height))  # Gradient effect
                    pygame.draw.line(gradient_surface, (0, 0, 0, alpha), (0, y), (character_width, y))
                self.screen.blit(gradient_surface, rect.topleft)

                # Draw the border for the character box
                pygame.draw.rect(self.screen, self.WHITE, rect, 3)

                # vẽ tên nhân vật(văn bản) lên khung
                self.draw_text(self.CHARACTER_DATA[i]["name"].upper(), self.controls_font, self.GREEN, 
                            start_x + i * (character_width + spacing) + character_width // 2, 190)
                if sprite_sheet:
            # Lấy frame đầu tiên từ spritesheet (giả sử mỗi frame có kích thước cố định)
                    frame_width = self.CHARACTER_DATA[i]["data"][0]  # Kích thước frame (ví dụ: WARRIOR_SIZE)
                    frame_height = frame_width  # Giả sử chiều cao bằng chiều rộng, điều chỉnh nếu cần
                    scale_factor=2.2
                    scale = self.CHARACTER_DATA[i]["data"][1]  # Scale factor
                    scaled_width = int(frame_width * scale_factor)  # Phóng to chiều rộng
                    scaled_height = int(frame_height * scale_factor)

            # Tạo surface cho frame đầu tiên (frame_index = 0, action = 0 - idle)
                    character_image = sprite_sheet.subsurface(pygame.Rect(0, 0, frame_width, frame_height))
                    
                    character_image = pygame.transform.scale(character_image, (scaled_width, scaled_height))

            # Tính toán vị trí để đặt hình ảnh dưới tên, căn giữa khung
                    image_x = start_x + i * (character_width + spacing) + (character_width - scaled_width) // 2
                    image_y = 140  # Đặt cách tên 50 pixel

            # Vẽ hình ảnh lên màn hình
                self.screen.blit(character_image, (image_x, image_y-50))

                # vẽ tên nhân vật trong mỗi ô
                # Use self.player_selection instead of the parameter
                if self.player_selection[0] == i:
                    self.draw_text("P1", self.title_font, self.WHITE, 
                                start_x + i * (character_width + spacing) + character_width // 2, 200)
                if self.player_selection[1] == i:
                    self.draw_text("P2", self.title_font, self.WHITE, 
                                start_x + i * (character_width + spacing) + character_width // 2, 250)
                                                # Vẽ instruction text
                self.draw_text("PLAYER 1: 1-4 KEYS TO SELECT", self.controls_font, self.GREEN, self.SCREEN_WIDTH // 2, 550)
                self.draw_text("PLAYER 2: 6-9 KEYS TO SELECT", self.controls_font, self.GREEN, self.SCREEN_WIDTH // 2, 600)
                self.draw_text("PRESS ENTER TO START", self.controls_font, self.GREEN, self.SCREEN_WIDTH // 2, 750)

        
    def draw_left_aligned_text(self, text, font, text_col, x, y): # x, y are top-left corner coordinates
        """Draw left-aligned text"""
        img = font.render(text, True, text_col) # Render text
        self.screen.blit(img, (x, y)) # Blit text on screen
     
    def draw_bg(self):
        """Draw background"""
        scaled_bg = pygame.transform.scale(self.bg_image, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT)) # Scale background image
        self.screen.blit(scaled_bg, (0, 0)) # Blit background on screen
    
    def draw_health_bar(self, health, x, y):
        """Draw health bar"""
        ratio = health / 100 # Calculate health ratio
        pygame.draw.rect(self.screen, self.WHITE, (x - 2, y - 2, 404, 34)) # Draw border
        pygame.draw.rect(self.screen, self.RED, (x, y, 400, 30)) # Draw red background
        pygame.draw.rect(self.screen, self.YELLOW, (x, y, 400 * ratio, 30)) # Draw yellow foreground based on health ratio
    
    def draw_controls_screen(self):
        """Draw controls screen"""
        # Draw dark translucent background
        s = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT)) # Create a surface for the background
        s.set_alpha(220) # Set alpha for transparency
        s.fill(self.BLACK) 
        self.screen.blit(s, (0, 0))
        
        # Draw title
        self.draw_text("KEYS TO PLAY", self.title_font, self.YELLOW, self.SCREEN_WIDTH // 2, 50)
        
        # Draw player 1 controls frame
        # Calculate new position for the player 1 controls frame
        frame_width = 400
        frame_height = 350
        frame_x = 30 # Align to the left edge of the screen
        frame_y = (self.SCREEN_HEIGHT - frame_height) // 2  # Center vertically

        # Draw player 1 controls frame
        # Draw player 1 controls frame with rounded corners
        # Add a subtle shadow effect for the frame
        shadow_rect = pygame.Rect(frame_x + 5, frame_y + 5, frame_width, frame_height)
        pygame.draw.rect(self.screen, (50, 50, 50), shadow_rect, border_radius=15)

        # Draw the main frame with rounded corners
        pygame.draw.rect(self.screen, self.BLACK, (frame_x, frame_y, frame_width, frame_height), border_radius=15)
        pygame.draw.rect(self.screen, self.WHITE, (frame_x, frame_y, frame_width, frame_height), 3, border_radius=15)

        # Add a title for the player 1 controls
        self.draw_text("PLAYER  1  CONTROLS ", self.controls_font, self.YELLOW, frame_x + frame_width // 2, frame_y + 40)

        # Adjust spacing and alignment for player 1 controls
        control_spacing = 40  # Space between each control line
        start_y = frame_y + 80  # Starting y-coordinate for controls
        self.draw_left_aligned_text("MOVE LEFT:    A", self.controls_font, self.GREEN, frame_x + 25, start_y)
        self.draw_left_aligned_text("MOVE RIGHT:   D", self.controls_font, self.GREEN, frame_x + 25, start_y + control_spacing)
        self.draw_left_aligned_text("JUMP:         W", self.controls_font, self.GREEN, frame_x + 25, start_y + 2 * control_spacing)
        self.draw_left_aligned_text("ATTACK 1:     R", self.controls_font, self.GREEN, frame_x + 25, start_y + 3 * control_spacing)
        self.draw_left_aligned_text("ATTACK 2:     T", self.controls_font, self.GREEN, frame_x + 25, start_y + 4 * control_spacing)
        self.draw_left_aligned_text("ATTACK 3:     Y", self.controls_font, self.GREEN, frame_x + 25, start_y + 5 * control_spacing)
        self.draw_left_aligned_text("CHAT:         C", self.controls_font, self.GREEN, frame_x + 25, start_y + 6 * control_spacing) # Chat control
        # Calculate new position for the player 2 controls frame
        frame_width = 400
        frame_height = 350
        frame_x = self.SCREEN_WIDTH - frame_width - 50  # 50px margin from the right edge
        frame_y = (self.SCREEN_HEIGHT - frame_height) // 2  # Center vertically

        # Draw player 2 controls frame
        # Add a subtle shadow effect for the frame
        shadow_rect = pygame.Rect(frame_x + 5, frame_y + 5, frame_width, frame_height)
        pygame.draw.rect(self.screen, (50, 50, 50), shadow_rect, border_radius=15)

        # Draw the main frame with rounded corners
        pygame.draw.rect(self.screen, self.BLACK, (frame_x, frame_y, frame_width, frame_height), border_radius=15)
        pygame.draw.rect(self.screen, self.WHITE, (frame_x, frame_y, frame_width, frame_height), 3, border_radius=15)

        # Add a title for the player 2 controls
        self.draw_text("PLAYER  2  CONTROLS", self.controls_font, self.YELLOW, frame_x + frame_width // 2, frame_y + 40)

        # Adjust spacing and alignment for player 2 controls
        control_spacing = 40  # Space between each control line
        start_y = frame_y + 80  # Starting y-coordinate for controls
        self.draw_left_aligned_text("MOVE LEFT:    Left Arrow", self.controls_font, self.GREEN, frame_x + 25, start_y)
        self.draw_left_aligned_text("MOVE RIGHT:   Right Arrow", self.controls_font, self.GREEN, frame_x + 25, start_y + control_spacing)
        self.draw_left_aligned_text("JUMP:         Up Arrow", self.controls_font, self.GREEN, frame_x + 25, start_y + 2 * control_spacing)
        self.draw_left_aligned_text("ATTACK 1:     J", self.controls_font, self.GREEN, frame_x + 25, start_y + 3 * control_spacing)
        self.draw_left_aligned_text("ATTACK 2:     K", self.controls_font, self.GREEN, frame_x + 25, start_y + 4 * control_spacing)
        self.draw_left_aligned_text("ATTACK 3:     L", self.controls_font, self.GREEN, frame_x + 25, start_y + 5 * control_spacing)
        self.draw_left_aligned_text("CHAT:         C", self.controls_font, self.GREEN, frame_x + 25, start_y + 6 * control_spacing) # Chat control
        
        # Display start prompt
        self.draw_text("PRESS SPACE TO CONTINUE", self.controls_font, self.GREEN, self.SCREEN_WIDTH // 2, 700) # Prompt to start game
    
    def waiting_screen(self):
        """Show waiting for other player screen"""
        # Draw dark translucent background
        s = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        s.set_alpha(220)
        s.fill(self.BLACK)
        self.screen.blit(s, (0, 0))
        
        # Draw waiting message
        self.draw_text("WAITING FOR OTHER PLAYER", self.title_font, self.YELLOW, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 50)
        self.draw_text("Please wait...", self.controls_font, self.WHITE, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 30)
    
    def connection_error_screen(self):
        """Show connection error screen"""
        # Draw dark background
        s = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT)) # Create a surface for the background
        s.set_alpha(255) # Set alpha for transparency
        s.fill(self.BLACK) # Fill with black color
        self.screen.blit(s, (0, 0)) # Blit the surface on the screen
        
        # Draw error message
        self.draw_text("CONNECTION ERROR", self.title_font, self.RED, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100)
        self.draw_text(f"Could not connect to server at {self.server}:{self.port}", 
                     self.controls_font, self.WHITE, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 30)
        
        if self.connection_error:
            # Split error message into multiple lines if needed
            error_lines = [self.connection_error[i:i+50] for i in range(0, len(self.connection_error), 50)]
            for i, line in enumerate(error_lines):
                self.draw_text(line, self.controls_font, self.WHITE, 
                              self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 10 + (i * 30))
        
        # Draw retry or exit options
        self.draw_text("Press 'R' to retry or 'ESC' to exit", self.controls_font, 
                     self.YELLOW, self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 100)
    #def display_victory_message(self):
    def display_game_over_messages(self):
        """Display victory or defeat message based on player ID and winner"""
        if not self.game_state or "winner" not in self.game_state: # Check if game state is valid
            return
            
        winner = self.game_state["winner"]
        
        # Create a semi-transparent overlay
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(self.BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Check if this client is the winner
        if (self.player_id == "player1" and winner == 1) or (self.player_id == "player2" and winner == 2):
            # Display VICTORY for the winner
            self.draw_text("VICTORY", self.game_over_font, self.GREEN, 
                         self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100)
        else:
            # Display DEFEAT for the loser
            self.draw_text("DEFEAT", self.game_over_font, self.RED, 
                         self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100)
    
    def display_round_result(self):
        if not self.game_state or "round_over" not in self.game_state or not self.game_state["round_over"]:
            return
    
    # Create a semi-transparent overlay
        overlay = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(self.BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Get the round winner from the game state if available
        # The server should be sending this information
        round_winner = self.game_state.get("round_winner", 0)
    
    # If round_winner isn't provided by the server, determine it from health values as fallback
        if round_winner == 0:
            if self.game_state["player1"]["health"] <= 0:
                round_winner = 2
            elif self.game_state["player2"]["health"] <= 0:
                round_winner = 1
            
    # Check if this client is the winner of the round
        if (self.player_id == "player1" and round_winner == 1) or (self.player_id == "player2" and round_winner == 2):
        # Display VICTORY for the round winner
            self.draw_text("ROUND WON", self.game_over_font, self.GREEN, 
                  self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100)
        elif round_winner > 0:  # Only show ROUND LOST if there is a definite winner
        # Display DEFEAT for the round loser
            self.draw_text("ROUND LOST", self.game_over_font, self.RED, 
                  self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100)
        else:
        # If no winner determined (could be a draw or error), display neutral message
            self.draw_text("ROUND OVER", self.game_over_font, self.YELLOW, 
                  self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100)
            
    def process_input(self):
        """Process player input during gameplay"""
        if (not self.game_state or
            self.game_state["round_over"] or
            self.game_state["intro_count"] > 0 or
            self.game_state["game_over"]):
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                pygame.quit()
                self.client.close()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    self.chat_active = not self.chat_active
                    if not self.chat_active:
                        self.chat_input = ""
                elif self.chat_active:
                    if event.key == pygame.K_RETURN:
                        if self.chat_input:
                            self.send_data({"chat": f"{self.player_id}: {self.chat_input}"})
                            self.chat_input = ""
                        self.chat_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.chat_input = self.chat_input[:-1]
                    elif event.key < 128:
                        self.chat_input += event.unicode

        if not self.chat_active and self.fighter_1 and self.fighter_2:
            if self.player_id == "player1":
                self.fighter_1.move(self.SCREEN_WIDTH, self.SCREEN_HEIGHT, self.screen, self.fighter_2, False)
            elif self.player_id == "player2":
                self.fighter_2.move(self.SCREEN_WIDTH, self.SCREEN_HEIGHT, self.screen, self.fighter_1, False)
            self.send_player_state()

    def send_player_state(self):
        """Send current player state to server with rate limiting"""
        current_time = pygame.time.get_ticks()
        
        # Only send updates at specified interval
        if current_time - self.last_update_time < self.update_interval: #Xác định khoảng thời gian tối thiểu giữa hai lần gửi dữ liệu, giúp giảm tải cho server và tiết kiệm băng thông.
            return
            
        self.last_update_time = current_time
        
        if self.player_id == "player1":
            self.send_data({
                "player_id": self.player_id,
                "x": self.fighter_1.rect.x,
                "y": self.fighter_1.rect.y,
                "health": self.fighter_1.health,
                "action": self.fighter_1.action,
                "frame_index": self.fighter_1.frame_index,
                "flip": self.fighter_1.flip,
                "attacking": self.fighter_1.attacking,
                "hit": self.fighter_1.hit
            })
        elif self.player_id == "player2":
            self.send_data({
                "player_id": self.player_id,
                "x": self.fighter_2.rect.x,
                "y": self.fighter_2.rect.y,
                "health": self.fighter_2.health,
                "action": self.fighter_2.action,
                "frame_index": self.fighter_2.frame_index,
                "flip": self.fighter_2.flip,
                "attacking": self.fighter_2.attacking,
                "hit": self.fighter_2.hit
            })
    
    def run(self):
        """Main game loop"""
        while True:
            # Attempt to connect if not connected
            if not self.connection_established and self.connection_retry_count == 0:
                if not self.connect():
                    # Failed to connect
                    pass
            
            # Game loop
            while self.running:
                self.clock.tick(self.FPS)
                
                # Check connection status
                if not self.connection_established:
                    self.connection_error_screen()
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_r]:
                        # Reset connection parameters
                        self.connection_retry_count = 0
                        break  # Break out of game loop to retry connection
                    elif keys[pygame.K_ESCAPE]:
                        pygame.quit()
                        self.client.close()
                        sys.exit()
                else:
                    # Draw background
                    self.draw_bg()
                    
                    # Check if we're in control screen
                    if self.show_controls:
                        self.draw_controls_screen()
                        key = pygame.key.get_pressed()
                        if key[pygame.K_SPACE]:
                            self.show_controls = False
                            self.character_selection = True
                    elif self.character_selection:
                        self.draw_character_selection()
                        selection_changed = False  # Initialize selection_changed to False
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                self.running = False
                                pygame.quit()
                                self.client.close()
                                sys.exit()
                            elif event.type == pygame.KEYDOWN:
                                #if self.player_id == "player1":
                                    if event.key == pygame.K_1:
                                        self.player_selection[0] = 0
                                        selection_changed = True
                                    elif event.key == pygame.K_2:
                                        self.player_selection[0] = 1
                                        selection_changed = True
                                    elif event.key == pygame.K_3:
                                        self.player_selection[0] = 2
                                        selection_changed = True
                                    elif event.key == pygame.K_4:
                                        self.player_selection[0] = 3
                                        selection_changed = True
                                # elif self.player_id == "player2":
                                    if event.key == pygame.K_6:
                                        self.player_selection[1] = 0
                                        selection_changed = True
                                    elif event.key == pygame.K_7:
                                        self.player_selection[1] = 1
                                        selection_changed = True
                                    elif event.key == pygame.K_8:
                                        self.player_selection[1] = 2
                                        selection_changed = True
                                    elif event.key == pygame.K_9:
                                        self.player_selection[1] = 3
                                        selection_changed = True
                                            
                            if selection_changed:
                                # Update character selection on server
                                self.send_data({"status": "selection_changed", "player_id": self.player_id,
                                                "selection": self.player_selection})
                            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                                self.send_data({"status": "selection_done", "player_id": self.player_id,
                                                "selection": self.player_selection[self.player_id[-1] == '2']})
                                self.send_data({"status": "ready", "player_id": self.player_id})
                        
                        # Exit character selection only when server confirms game_active
                        if self.game_state and self.game_state.get("game_active", False):
                            self.character_selection = False
                      
                    else:
                        # If we have game state and game is active
                        if self.game_state and "game_active" in self.game_state :
                            if not self.game_state["game_active"]:
                                # Show waiting screen
                                self.waiting_screen()
                            else : 
                                if not self.fighter_1 and not self.fighter_2:
                                    self.create_fighters()
                            
                                # Update health bars
                                if "player1" in self.game_state and "health" in self.game_state["player1"]:
                                    self.draw_health_bar(self.game_state["player1"]["health"], 20, 20)
                                if "player2" in self.game_state and "health" in self.game_state["player2"]:
                                    self.draw_health_bar(self.game_state["player2"]["health"], self.SCREEN_WIDTH - 420, 20)
                                
                                # Update scores
                                if "scores" in self.game_state:
                                    self.draw_left_aligned_text("P1: " + str(self.game_state["scores"][0]), self.score_font, self.RED, 20, 60)
                                    self.draw_left_aligned_text("P2: " + str(self.game_state["scores"][1]), self.score_font, self.RED, self.SCREEN_WIDTH - 20 - self.score_font.size("P2: " + str(self.game_state["scores"][1]))[0], 60)
                                
                                # Check if round is over
                                if "round_over" in self.game_state and self.game_state["round_over"] and not self.game_state["game_over"]:
                                    self.display_round_result()
                                elif "intro_count" in self.game_state and self.game_state["intro_count"] > 0:
                                    # Display count timer
                                    self.draw_text(str(self.game_state["intro_count"]), self.count_font, self.RED, 
                                                 self.SCREEN_WIDTH / 2, self.SCREEN_HEIGHT / 3)
                                else:
                                    # Process player input
                                    self.process_input()
                                
                                # Update fighters
                                self.fighter_1.update()
                                self.fighter_2.update()
                                
                                # Draw fighters
                                self.fighter_1.draw(self.screen)
                                self.fighter_2.draw(self.screen)
                                
                                # Check for game over
                                if "game_over" in self.game_state and self.game_state["game_over"]:
                                    # Display custom victory/defeat message based on player
                                    self.display_game_over_messages()
                                # Check if chat messages should still be displayed
                                if self.show_chat_messages:
                                    current_time = pygame.time.get_ticks()
                                    if current_time - self.chat_display_timer >= self.CHAT_DISPLAY_DURATION:
                                     self.show_chat_messages = False
                                
                                # Display chat messages
                               # Display chat messages
                                if self.chat_messages and self.show_chat_messages:
                                    # Create a semi-transparent background for chat area
                                    chat_bg = pygame.Surface((300, 100))
                                    chat_bg.set_alpha(150)
                                    chat_bg.fill(self.BLACK)
                                    self.screen.blit(chat_bg, (250, 430))
                                    
                                    # Display most recent messages (limited by max_chat_messages)
                                    recent_messages = self.chat_messages[-self.max_chat_messages:]
                                    for i, msg in enumerate(recent_messages):
                                        # Determine message color based on player
                                        if msg.startswith("player1:"):
                                            msg_color = self.WHITE
                                        elif msg.startswith("player2:"):
                                            msg_color = self.WHITE
                                        else:
                                            msg_color = self.WHITE
                                        
                                        # Draw message text
                                        input_text=pygame.font.SysFont(None, 30).render(msg, True, msg_color)
                                        self.screen.blit(input_text, (260, 440 + i * 25))
                                        #self.draw_left_aligned_text(msg, self.controls_font, msg_color, 260, 440 + i * 25)
                                
                                # Display chat input if active
                                if self.chat_active:
                                    # Vẽ nền ô chat với viền bo góc
                                    input_bg = pygame.Surface((700, 50))  # Giảm kích thước cho cân đối
                                    input_bg.set_alpha(220)  # Tăng độ trong suốt nhẹ
                                    input_bg.fill(self.LIGHT_GRAY)  # Sử dụng màu xám nhạt thay đen
                                    pygame.draw.rect(input_bg, self.GRAY, (0, 0, 700, 50), 2, border_radius=10)  # Viền bo góc
                                    self.screen.blit(input_bg, (100, 400))  # Dịch xuống dưới cùng

                                    # Vẽ văn bản với font đẹp hơn
                                    font = pygame.font.Font(None, 32)  # Font mặc định, cỡ 32
                                    input_text = f"Chat: {self.chat_input}"
                                    input_surface = font.render(input_text, True, self.BLACK)  # Chữ đen trên nền xám
                                    text_rect = input_surface.get_rect(center=(100 + 350, 400 + 25))  # Căn giữa ô
                                    self.screen.blit(input_surface, text_rect)

                                                    # Thêm placeholder khi chưa nhập
                                    
                                    # Draw blinking cursor
                                    if pygame.time.get_ticks() % 1000 < 500:  # Blink every half second
                                        cursor_x = 110 + self.controls_font.size(input_text)[0]
                                        pygame.draw.line(self.screen, self.GREEN, (cursor_x, 395), (cursor_x, 420), 2)
                
                # Update display
                pygame.display.update()
                
                # Handle events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        pygame.quit()
                        self.client.close()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            if self.chat_active:
                                # Close chat if open
                                self.chat_active = False
                                self.chat_input = ""
                            elif self.game_state and self.game_state.get("game_over", False):
                                # Exit game if game is over
                                self.running = False
                                pygame.quit()
                                self.client.close()
                                sys.exit()

            # If we reach here, we've broken out of the game loop
            # Check if we should retry connection
            if not self.connection_established and self.connection_retry_count < self.max_retries:
                print("Retrying connection...")
                continue  # Go back to main loop and try to connect again
            else:
                # Either connected successfully or gave up trying
                pygame.quit()
                self.client.close()
                sys.exit()

def main():
    """Main function"""
    # Try to read server address from command line arguments
    server_host = 'localhost'
    server_port = 5555
    
    if len(sys.argv) > 1:
        server_host = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            server_port = int(sys.argv[2])
        except ValueError:
            print(f"Invalid port number: {sys.argv[2]}. Using default port 5555.")
    
    # Create and run game client
    game = GameClient(host=server_host, port=server_port)
    game.run()

if __name__ == "__main__":
    main()