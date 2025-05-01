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
        self.server = host
        self.port = port
        self.addr = (self.server, self.port)
        self.player_id = None
        self.game_state = None
        self.running = True
        self.connection_established = False
        self.connection_error = None
        self.connection_retry_count = 0
        self.max_retries = 3
        
        # Track previous round_over state to detect new rounds
        self.was_round_over = False
        
        # Initialize pygame and mixer
        mixer.init()
        pygame.init()
        
        # Game window setup
        self.SCREEN_WIDTH = 1000
        self.SCREEN_HEIGHT = 600
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
        
        # Game variables
        self.intro_count = 5
        self.last_count_update = pygame.time.get_ticks()
        self.round_over = False
        self.ROUND_OVER_COOLDOWN = 2000
        self.game_over = False
        self.WIN_SCORE = 5
        self.winner = 0
        self.show_controls = True
        
        # Fighter variables
        self.WARRIOR_SIZE = 162
        self.WARRIOR_SCALE = 4
        self.WARRIOR_OFFSET = [72, 56]
        self.WARRIOR_DATA = [self.WARRIOR_SIZE, self.WARRIOR_SCALE, self.WARRIOR_OFFSET]
        self.WIZARD_SIZE = 250
        self.WIZARD_SCALE = 3
        self.WIZARD_OFFSET = [112, 107]
        self.WIZARD_DATA = [self.WIZARD_SIZE, self.WIZARD_SCALE, self.WIZARD_OFFSET]
        
        # Load resources
        self.load_resources()
        
        # Create fighters
        self.fighter_1 = Fighter(1, 200, 310, False, self.WARRIOR_DATA, self.warrior_sheet, 
                                [10, 8, 1, 7, 7, 3, 7], self.sword_fx)
        self.fighter_2 = Fighter(2, 700, 310, True, self.WIZARD_DATA, self.wizard_sheet, 
                                [8, 8, 1, 8, 8, 3, 7], self.magic_fx)
        
        # Store initial positions for resetting
        self.fighter_1_initial_x = 200
        self.fighter_1_initial_y = 310
        self.fighter_2_initial_x = 700
        self.fighter_2_initial_y = 310
        
        # Network update rate (to prevent flooding the server)
        self.last_update_time = 0
        self.update_interval = 1000 / 30  # 30 updates per second
        
    def load_resources(self):
        """Load game resources"""
        try:
            # Load music and sounds
            pygame.mixer.music.load("assets/audio/ok.mp3")
            pygame.mixer.music.set_volume(1)
            pygame.mixer.music.play(-1, 0.0, 5000)
            self.sword_fx = pygame.mixer.Sound("assets/audio/sword.wav")
            self.sword_fx.set_volume(0.5)
            self.magic_fx = pygame.mixer.Sound("assets/audio/magic.wav")
            self.magic_fx.set_volume(0.75)
            
            # Load background image
            self.bg_image = pygame.image.load("assets/images/background/background.jpg").convert_alpha()
            
            # Load spritesheets
            self.warrior_sheet = pygame.image.load("assets/images/warrior/Sprites/warrior.png").convert_alpha()
            self.wizard_sheet = pygame.image.load("assets/images/wizard/Sprites/wizard.png").convert_alpha()
            
            # Load victory image
            self.victory_img = pygame.image.load("assets/images/icons/victory.png").convert_alpha()
            
            # Define fonts
            self.count_font = pygame.font.Font("assets/fonts/turok.ttf", 80)
            self.score_font = pygame.font.Font("assets/fonts/turok.ttf", 30)
            self.game_over_font = pygame.font.Font("assets/fonts/turok.ttf", 50)
            self.controls_font = pygame.font.Font("assets/fonts/turok.ttf", 25)
            self.title_font = pygame.font.Font("assets/fonts/turok.ttf", 40)
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
                self.client.connect(self.addr)
                
                # Reset timeout to None (blocking mode) for normal operation
                self.client.settimeout(None)
                
                print(f"Connected to server at {self.addr}")
                
                # Receive player ID from server
                data = self.client.recv(4096)
                if not data:
                    raise Exception("No data received from server")
                    
                response = pickle.loads(data)
                
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
                time.sleep(1)
        
        # If we've exhausted our retries
        if not self.connection_established:
            print("Failed to connect to server after multiple attempts")
            return False
    
    def receive_data(self):
        """Continuously receive data from server"""
        self.client.settimeout(5)  # Set timeout to detect disconnection
        
        while self.running:
            try:
                data = self.client.recv(4096)
                if not data:
                    print("Server disconnected (no data)")
                    break
                    
                self.game_state = pickle.loads(data)
                
                # Update local game state based on server data
                if self.game_state and "game_active" in self.game_state:
                    # Check for round state changes
                    new_round_over = self.game_state["round_over"]
                    
                    # Detect round transitions (was over, now starting new round)
                    if self.was_round_over and not new_round_over:
                        print("New round starting - resetting local fighter state")
                        # Reset local state for controlled fighter
                        if self.player_id == "player1":
                            self.reset_fighter_state(self.fighter_1, self.fighter_1_initial_x, self.fighter_1_initial_y)
                        elif self.player_id == "player2":
                            self.reset_fighter_state(self.fighter_2, self.fighter_2_initial_x, self.fighter_2_initial_y)
                    
                    # Update round state
                    self.was_round_over = new_round_over
                    self.round_over = new_round_over
                    self.game_over = self.game_state["game_over"]
                    self.winner = self.game_state["winner"]
                    
                    if self.game_state["game_active"]:
                        # Update fighter states based on player role
                        if self.player_id == "player1":
                            # For player1: Only update health from server (in case of taking damage)
                            self.fighter_1.health = self.game_state["player1"]["health"]
                            self.fighter_1.hit = self.game_state["player1"]["hit"]
                            
                            # Update entire state of opponent
                            if "player2" in self.game_state:
                                self.fighter_2.rect.x = self.game_state["player2"]["x"]
                                self.fighter_2.rect.y = self.game_state["player2"]["y"]
                                self.fighter_2.health = self.game_state["player2"]["health"]
                                self.fighter_2.action = self.game_state["player2"]["action"]
                                self.fighter_2.frame_index = self.game_state["player2"]["frame_index"]
                                self.fighter_2.flip = self.game_state["player2"]["flip"]
                                self.fighter_2.attacking = self.game_state["player2"]["attacking"]
                                self.fighter_2.hit = self.game_state["player2"]["hit"]
                                
                        elif self.player_id == "player2":
                            # For player2: Only update health from server (in case of taking damage)
                            self.fighter_2.health = self.game_state["player2"]["health"]
                            self.fighter_2.hit = self.game_state["player2"]["hit"]
                            
                            # Update entire state of opponent
                            if "player1" in self.game_state:
                                self.fighter_1.rect.x = self.game_state["player1"]["x"]
                                self.fighter_1.rect.y = self.game_state["player1"]["y"]
                                self.fighter_1.health = self.game_state["player1"]["health"]
                                self.fighter_1.action = self.game_state["player1"]["action"]
                                self.fighter_1.frame_index = self.game_state["player1"]["frame_index"]
                                self.fighter_1.flip = self.game_state["player1"]["flip"]
                                self.fighter_1.attacking = self.game_state["player1"]["attacking"]
                                self.fighter_1.hit = self.game_state["player1"]["hit"]
                
            except socket.timeout:
                # Just retry on timeout
                continue
            except ConnectionResetError:
                print("Connection reset by server")
                break
            except ConnectionAbortedError:
                print("Connection aborted")
                break
            except Exception as e:
                print(f"Error receiving data: {e}")
                break
                
        print("Disconnected from server")
        self.connection_established = False
        self.running = False
        
    def send_data(self, data):
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
            self.connection_established = False
            self.running = False
    
    def draw_text(self, text, font, text_col, x, y):
        """Draw text on screen"""
        img = font.render(text, True, text_col)
        text_rect = img.get_rect(center=(x, y))
        self.screen.blit(img, text_rect)
    
    def draw_left_aligned_text(self, text, font, text_col, x, y):
        """Draw left-aligned text"""
        img = font.render(text, True, text_col)
        self.screen.blit(img, (x, y))
    
    def draw_bg(self):
        """Draw background"""
        scaled_bg = pygame.transform.scale(self.bg_image, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        self.screen.blit(scaled_bg, (0, 0))
    
    def draw_health_bar(self, health, x, y):
        """Draw health bar"""
        ratio = health / 100
        pygame.draw.rect(self.screen, self.WHITE, (x - 2, y - 2, 404, 34))
        pygame.draw.rect(self.screen, self.RED, (x, y, 400, 30))
        pygame.draw.rect(self.screen, self.YELLOW, (x, y, 400 * ratio, 30))
    
    def draw_controls_screen(self):
        """Draw controls screen"""
        # Draw dark translucent background
        s = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        s.set_alpha(220)
        s.fill(self.BLACK)
        self.screen.blit(s, (0, 0))
        
        # Draw title
        self.draw_text("KEYS TO PLAY", self.title_font, self.YELLOW, self.SCREEN_WIDTH // 2, 50)
        
        # Draw player 1 controls frame
        pygame.draw.rect(self.screen, self.BLUE, (50, 120, 400, 350), 0)
        pygame.draw.rect(self.screen, self.WHITE, (50, 120, 400, 350), 3)
        
        # Draw player 1 controls
        self.draw_left_aligned_text("Player 1 (WARRIOR)", self.controls_font, self.WHITE, 75, 130)
        self.draw_left_aligned_text("Left:         A", self.controls_font, self.WHITE, 75, 180)
        self.draw_left_aligned_text("Right:        D", self.controls_font, self.WHITE, 75, 220)
        self.draw_left_aligned_text("Up:           W", self.controls_font, self.WHITE, 75, 260)
        self.draw_left_aligned_text("Attack 1:     R", self.controls_font, self.WHITE, 75, 300)
        self.draw_left_aligned_text("Attack 2:     T", self.controls_font, self.WHITE, 75, 340)
        self.draw_left_aligned_text("Attack 3:     Y", self.controls_font, self.WHITE, 75, 380)
        
        # Draw player 2 controls frame
        pygame.draw.rect(self.screen, self.RED, (550, 120, 400, 350), 0)
        pygame.draw.rect(self.screen, self.WHITE, (550, 120, 400, 350), 3)
        
        # Draw player 2 controls
        self.draw_left_aligned_text("Player 2 (WIZARD)", self.controls_font, self.WHITE, 575, 130)
        self.draw_left_aligned_text("Left:         ←", self.controls_font, self.WHITE, 575, 180)
        self.draw_left_aligned_text("Right:        →", self.controls_font, self.WHITE, 575, 220)
        self.draw_left_aligned_text("Up:           ↑", self.controls_font, self.WHITE, 575, 260)
        self.draw_left_aligned_text("Attack 1:     J", self.controls_font, self.WHITE, 575, 300)
        self.draw_left_aligned_text("Attack 2:     K", self.controls_font, self.WHITE, 575, 340)
        self.draw_left_aligned_text("Attack 3:     L", self.controls_font, self.WHITE, 575, 380)
        
        # Display start prompt
        self.draw_text("Press Space to continue", self.controls_font, self.GREEN, self.SCREEN_WIDTH // 2, 500)
    
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
        s = pygame.Surface((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        s.set_alpha(255)
        s.fill(self.BLACK)
        self.screen.blit(s, (0, 0))
        
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
    
    def send_player_state(self):
        """Send current player state to server with rate limiting"""
        current_time = pygame.time.get_ticks()
        
        # Only send updates at specified interval
        if current_time - self.last_update_time < self.update_interval:
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
    
    def process_input(self):
        """Process player input"""
        # Don't process input if:
        # 1. No game state
        # 2. Round is over
        # 3. Intro is still counting down
        # 4. Game is over
        if (not self.game_state or 
            self.game_state["round_over"] or 
            self.game_state["intro_count"] > 0 or
            self.game_state["game_over"]):
            return
            
        # Update fighter based on player_id
        if self.player_id == "player1":
            self.fighter_1.move(self.SCREEN_WIDTH, self.SCREEN_HEIGHT, self.screen, self.fighter_2, False)
        elif self.player_id == "player2":
            self.fighter_2.move(self.SCREEN_WIDTH, self.SCREEN_HEIGHT, self.screen, self.fighter_1, False)
        
        self.send_player_state()
    
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
                
                # Process events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        pygame.quit()
                        self.client.close()
                        sys.exit()
                
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
                            # Tell server we're ready
                            self.send_data({"status": "ready", "player_id": self.player_id})
                    else:
                        # If we have game state and game is active
                        if self.game_state and "game_active" in self.game_state:
                            if not self.game_state["game_active"]:
                                # Show waiting screen
                                self.waiting_screen()
                            else:
                                # Update health bars
                                if "player1" in self.game_state and "health" in self.game_state["player1"]:
                                    self.draw_health_bar(self.game_state["player1"]["health"], 20, 20)
                                if "player2" in self.game_state and "health" in self.game_state["player2"]:
                                    self.draw_health_bar(self.game_state["player2"]["health"], 580, 20)
                                
                                # Update scores
                                if "scores" in self.game_state:
                                    self.draw_left_aligned_text("P1: " + str(self.game_state["scores"][0]), self.score_font, self.RED, 20, 60)
                                    self.draw_left_aligned_text("P2: " + str(self.game_state["scores"][1]), self.score_font, self.RED, 580, 60)
                                
                                # Check if round is over
                                if "round_over" in self.game_state and self.game_state["round_over"]:
                                    # Display victory image
                                    victory_rect = self.victory_img.get_rect(center=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 50))
                                    self.screen.blit(self.victory_img, victory_rect)
                                elif "intro_count" in self.game_state and self.game_state["intro_count"] > 0:
                                    # Display count timer
                                    self.draw_text(str(self.game_state["intro_count"]), self.count_font, self.RED, 
                                                 self.SCREEN_WIDTH / 2, self.SCREEN_HEIGHT / 3)
                                else:
                                    # Process player input
                                    self.process_input()
                                
                                # Check for game over
                                if "game_over" in self.game_state and self.game_state["game_over"]:
                                    # Display game over message
                                    self.draw_text(f"PLAYER {self.game_state['winner']} WINS!", self.game_over_font, self.BLUE, 
                                                 self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 100)
                                    self.draw_text("Waiting for server to restart...", self.score_font, self.WHITE, 
                                                 self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2)
                                
                                # Update fighters
                                self.fighter_1.update()
                                self.fighter_2.update()
                                
                                # Draw fighters
                                self.fighter_1.draw(self.screen)
                                self.fighter_2.draw(self.screen)
                        
                        else:
                            # Show waiting screen if no game state yet
                            self.waiting_screen()
                
                # Update display
                pygame.display.update()
            
            # If we're exiting properly
            if self.connection_retry_count >= self.max_retries:
                break

        # Clean up when done
        pygame.quit()
        try:
            self.client.close()
        except:
            pass
        sys.exit()

if __name__ == "__main__":
    # Get server IP from command line or use localhost
    server_ip = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    client = GameClient(host=server_ip)
    client.run()