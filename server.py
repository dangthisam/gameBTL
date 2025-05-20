import socket # For socket handling
import pickle # For object serialization
import threading # For thread handling
import time # For time handling
import json

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555):
        #AF-INET: IPv4, SOCK_STREAM: TCP
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Enable reuse of the address to avoid "Address already in use" errors
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(2)  # Accept only 2 connections (2 players)
       # self.game_state = {"player_selections": [0, 0], "game_active": False}
        print(f"Server running and listening on {host}:{port}")
        self.SCREEN_WIDTH = 1300
        self.SCREEN_HEIGHT = 800
        
        # Initial player states for reset
        # Player 1 state
        self.initial_player1_state = {
            "x": 100,  # Position player 1 at the bottom-left corner
            "y": self.SCREEN_HEIGHT - 200,  # Near the bottom of the screen
            "health": 100,
            "action": 0,
            "frame_index": 0,
            "flip": False,
            "attacking": False,
            "hit": False
        }
        # Player 2 state is flipped horizontally
        # Position player 2 at the bottom-right corner
        self.initial_player2_state = {
            "x": self.SCREEN_WIDTH - 150,  # Near the bottom-right corner
            "y": self.SCREEN_HEIGHT-300,  # Near the bottom of the screen
            "health": 100,
            "action": 0,
            "frame_index": 0,
            "flip": True,
            "attacking": False,
            "hit": False
        }
        
        # Game state that matches client expectations
        self.game_state = {
            "player1": dict(self.initial_player1_state),
            "player2": dict(self.initial_player2_state),
            "game_active": False,   # Game starts when both players are ready
            "round_over": False,    # Round state
            "intro_count": 5,       # Countdown at start of round
            "scores": [0, 0],       # Player scores
            "game_over": False,     # Game over state
            "winner": 0,   ## Winner ID (1 or 2)
            "player_selections": [0, 0], ## Player character selections (0-3)
            "chat_messages": []     ## List to store chat messages
        }
        
        # Thread safety
        self.state_lock = threading.Lock() ## Lock for game state updates
        
        self.clients = [] # List of connected clients
        self.player_ids = {}  # Map socket to player ID
        self.ready_players = set() ## Track ready players
        self.selections_done = set()  # Track players who have selected characters  # Track ready players
        self.selection_done = {"player1": False, "player2": False} # Track players who have selected characters
        
        self.round_start_time = 0
        self.last_count_update = 0
        self.round_over_time = 0
        self.WIN_SCORE = 5
        
        # Track last hit times for each player
        self.last_hit_times = {"player1": 0, "player2": 0}
        self.HIT_RESET_DELAY = 0.5  # Reset hit state after 0.5 seconds
        ## Cooldown time after round over


    def handle_client(self, client, player_id):
        """Handle connection from a specific client"""
        try:
            # Send initial game state
            with self.state_lock:
                serialized_state = pickle.dumps(self.game_state)
            client.send(serialized_state)  # Send initial game state to the client
            
            while True:  # Loop to receive data from client
                # Receive data from client with timeout
                client.settimeout(1.0)  # 1-second timeout for receiving data
                try:
                    data = client.recv(4096)
                    if not data:
                        print(f"No data received from {player_id}, client disconnected")
                        break
                except socket.timeout:
                    # This is fine, just continue the loop
                    continue
                except ConnectionResetError:
                    print(f"Connection reset by {player_id}")
                    break
                except Exception as e:
                    print(f"Error receiving data from {player_id}: {e}")
                    break
                
                # Decode received data
                try:
                    client_data = pickle.loads(data)
                    print("data" , client_data)  # Deserialize the data
                    
                    # Handle selection_update
                    if client_data.get("status") in ("selection_update", "selection_changed"):
                        sel_index = client_data.get("selection")
                        if player_id == "player1":
                            self.game_state["player_selections"][0] = sel_index
                        elif player_id == "player2":
                            self.game_state["player_selections"][1] = sel_index
                        print(f"{player_id} updated selection to {sel_index}")
                        
                        # Broadcast updated game state
                        self.broadcast_game_state()
                        continue
                    
                    # Handle chat messages
                    if "chat" in client_data:
                        with self.state_lock:
                            self.game_state["chat_messages"].append(client_data["chat"])
                            # Limit the number of messages (e.g., max 50 messages)
                            if len(self.game_state["chat_messages"]) > 50:
                                self.game_state["chat_messages"] = self.game_state["chat_messages"][-50:]
                    
                    # Process ready status
                    elif "status" in client_data and client_data["status"] == "ready":
                        self.ready_players.add(player_id)
                        print(f"{player_id} is ready. Ready players: {self.ready_players}")
                        
                        # If both players are ready, start the game
                        if len(self.ready_players) == 2 and not self.game_state["game_active"]:
                            print("Both players ready, starting game!")
                            with self.state_lock:
                                self.game_state["game_active"] = True
                                self.game_state["intro_count"] = 5
                                self.game_state["round_over"] = False
                                self.game_state["game_over"] = False
                                # Reset player states to initial values
                                self.game_state["player1"] = dict(self.initial_player1_state)
                                self.game_state["player2"] = dict(self.initial_player2_state)
                            self.round_start_time = time.time()
                            self.last_count_update = self.round_start_time
                    
                    # Update player state if it's a player update
                    elif "player_id" in client_data and client_data["player_id"] == player_id:
                        with self.state_lock:
                            # Update all received player attributes
                            for key, value in client_data.items():
                                if key != "player_id" and key in self.game_state[player_id]:
                                    self.game_state[player_id][key] = value
                            
                        # Process any attack interactions
                        self.process_attack_interactions()
                    
                except Exception as e:
                    print(f"Error processing data from {player_id}: {e}")
            
        except Exception as e:
            print(f"Error handling client {player_id}: {e}")
        finally:
            # Clean up when client disconnects
            print(f"{player_id} has disconnected")
            if client in self.clients:
                self.clients.remove(client)
            if client in self.player_ids:
                del self.player_ids[client]
            if player_id in self.ready_players:
                self.ready_players.remove(player_id)
            
            try:
                client.close()
            except:
                pass
                
            # Update game state
            with self.state_lock:
                self.game_state["game_active"] = False
                
            # Broadcast to remaining clients
            self.broadcast_game_state()  # Send updated state to remaining clients

    def periodic_broadcast(self):
        """Periodically broadcast game state to all clients"""
        while True:
            try:
                self.broadcast_game_state()
                time.sleep(0.1)  # Broadcast every 0.1 seconds
            except Exception as e:
                print(f"Error in periodic broadcast: {e}")
            
    def process_attack_interactions(self):
        """Process attack interactions between players"""
        current_time = time.time() # Get current time for hit reset logic
        
        with self.state_lock:
            if not self.game_state["game_active"] or self.game_state["round_over"]: # Check if game is active and round is not over
                # If game is not active or round is over, skip processing
                return
                
            p1 = self.game_state["player1"] ## Player 1 state
            p2 = self.game_state["player2"] ## Player 2 state
            
            # Reset hit states if enough time has passed since last hit
            if p1["hit"] and current_time - self.last_hit_times["player1"] >= self.HIT_RESET_DELAY:
                p1["hit"] = False
                
            if p2["hit"] and current_time - self.last_hit_times["player2"] >= self.HIT_RESET_DELAY:
                p2["hit"] = False
            
            # Check if player 1 is attacking player 2
            if p1["attacking"] and not p2["hit"]:
                # Simple hit detection - adjust based on your fighter implementation
                # This is a simplified version assuming rectangular hit detection
                p1_right = p1["x"] + 100  # Estimated attack range
                p2_left = p2["x"] - 50     # Estimated position adjustment
                
                if p1_right > p2_left and p1["y"] - 50 < p2["y"] + 50 and p1["y"] + 50 > p2["y"] - 50: # Check if player 1's attack hits player 2
                    # Hit detected
                    p2["health"] -= 5 # Damage amount
                    p2["hit"] = True
                    self.last_hit_times["player2"] = current_time
                    
                    # Check for round end
                    if p2["health"] <= 0:
                        p2["health"] = 0
                        self.game_state["round_over"] = True
                        self.game_state["scores"][0] += 1 # Increment player 1's score
                        self.round_over_time = time.time() # Store round over time
                    
            # Check if player 2 is attacking player 1
            if p2["attacking"] and not p1["hit"]:
                # Simple hit detection
                p2_left = p2["x"] - 100   # Estimated attack range (for player 2 attacking left)
                p1_right = p1["x"] + 50   # Estimated position adjustment
                
                if p2_left < p1_right and p2["y"] - 50 < p1["y"] + 50 and p2["y"] + 50 > p1["y"] - 50:
                    # Hit detected
                    p1["health"] -= 5  # Damage amount
                    p1["hit"] = True
                    self.last_hit_times["player1"] = current_time
                    
                    # Check for round end
                    if p1["health"] <= 0:
                        p1["health"] = 0
                        self.game_state["round_over"] = True
                        self.game_state["scores"][1] += 1
                        self.round_over_time = time.time()
            
            # Check for game over
            if self.game_state["scores"][0] >= self.WIN_SCORE:
                self.game_state["game_over"] = True
                self.game_state["winner"] = 1
            elif self.game_state["scores"][1] >= self.WIN_SCORE:
                self.game_state["game_over"] = True
                self.game_state["winner"] = 2
                
    def update_game_state(self): #update game state based on time
        """Update game state based on time"""
        current_time = time.time()
        
        with self.state_lock:
            # Update countdown
            if self.game_state["game_active"] and not self.game_state["round_over"] and self.game_state["intro_count"] > 0:
                if current_time - self.last_count_update >= 1.0:  # 1 second interval
                    self.game_state["intro_count"] -= 1
                    self.last_count_update = current_time
            
            # Handle round over cooldown
            if self.game_state["round_over"] and not self.game_state["game_over"]:
                if current_time - self.round_over_time >= 2.0:  # 2 second cooldown
                    # Reset for next round
                    self.game_state["round_over"] = False
                    self.game_state["intro_count"] = 5
                    
                    # Reset player states completely by assigning fresh copies of initial states
                    self.game_state["player1"] = dict(self.initial_player1_state)
                    self.game_state["player2"] = dict(self.initial_player2_state)
                    
                    self.round_start_time = current_time
                    self.last_count_update = current_time
                    
    def broadcast_game_state(self):
        """Send current game state to all clients"""
        with self.state_lock:
            serialized_state = pickle.dumps(self.game_state) # Serialize the game state
            
        for client in self.clients[:]:  # Copy the list to avoid modification during iteration
            try:
                client.send(serialized_state) # Send the serialized game state to each client
            except Exception as e:
                print(f"Error sending to client: {e}")
                # Don't remove here to avoid modifying the list during iteration
                # The client will be removed in the handle_client function when it detects the error
                
    def game_loop(self):
        """Main game loop that runs in the background"""
        while True:
            try:
                # Update game state based on time
                self.update_game_state()
                
                # Broadcast updated state to all clients
                if self.clients:  # Only broadcast if we have clients
                    self.broadcast_game_state()
                
                # Sleep to prevent CPU overuse
                time.sleep(1/30)  # ~30 updates per second
                
            except Exception as e:
                print(f"Error in game loop: {e}")
                
    def run(self):
        """Run server and accept connections"""
        try:
            # Start the game loop in a separate thread
            game_thread = threading.Thread(target=self.game_loop)
            game_thread.daemon = True # Daemonize thread to exit when main program exits
            game_thread.start()
            
            print("Waiting for players to connect...")
            while True:
                # Set a timeout for accept to allow for server shutdown
                self.server.settimeout(1.0)
                try:
                    client, addr = self.server.accept()
                    print(f"Connection from {addr}")
                    
                    # Set client socket options
                    client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) #Tắt chế độ Nagle (TCP_NODELAY), giúp giảm độ trễ khi gửi dữ liệu qua mạng.
                    
                    # Check if we can accept more players
                    if len(self.clients) < 2:
                        player_id = f"player{len(self.clients) + 1}"
                        
                        # Store client info
                        self.clients.append(client)
                        self.player_ids[client] = player_id
                        
                        # Send ID to client
                        response = {"player_id": player_id}
                        client.send(pickle.dumps(response))
                        
                        # Create thread to handle this client
                        client_thread = threading.Thread(target=self.handle_client, args=(client, player_id))
                        client_thread.daemon = True
                        client_thread.start()
                        
                        print(f"Player {player_id} connected. Total players: {len(self.clients)}")
                    else:
                        # Reject connection if room is full
                        try:
                            client.send(pickle.dumps({"error": "Room is full"}))
                            client.close()
                        except:
                            pass
                except socket.timeout:
                    # This is normal, just continue the loop
                    continue
                except Exception as e:
                    print(f"Error accepting connection: {e}")
                    
        except KeyboardInterrupt:
            print("Server shutting down...")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            # Clean up
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.server.close()
            print("Server closed")

if __name__ == "__main__":
    server = GameServer()
    server.run()