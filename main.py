import pygame
from pygame import mixer
from fighter import Fighter

mixer.init()
pygame.init()

#create game window
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

#Title and icon
pygame.display.set_caption("Brawler")

#set framerate
clock = pygame.time.Clock()
FPS = 60

#define colours
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)

#define game variables
#dem nguoc trươc khi choi vao game
intro_count = 5
last_count_update = pygame.time.get_ticks()
score = [0, 0]#player scores. [P1, P2]
#kiem tra vòng chơi đã kết thúc hay chưa
round_over = False
#chờ 2s để bắt đầu vòng chơi mới
ROUND_OVER_COOLDOWN = 2000
#Thêm biến để theo dõi khi trò chơi kết thúc
game_over = False
#Số điểm để thắng trò chơi
WIN_SCORE = 5
#Biến để xác định ai là người thắng
winner = 0
#Thêm biến cho màn hình hướng dẫn
show_controls = True

#define fighter variables
WARRIOR_SIZE = 162
WARRIOR_SCALE = 4
WARRIOR_OFFSET = [72, 56]
WARRIOR_DATA = [WARRIOR_SIZE, WARRIOR_SCALE, WARRIOR_OFFSET]
WIZARD_SIZE = 250
WIZARD_SCALE = 3
WIZARD_OFFSET = [112, 107]
WIZARD_DATA = [WIZARD_SIZE, WIZARD_SCALE, WIZARD_OFFSET]

#load music and sounds
pygame.mixer.music.load("assets/audio/ok.mp3")
pygame.mixer.music.set_volume(1)
#nhac lặp vô hạn
pygame.mixer.music.play(-1, 0.0, 5000)
sword_fx = pygame.mixer.Sound("assets/audio/sword.wav")
sword_fx.set_volume(0.5)
magic_fx = pygame.mixer.Sound("assets/audio/magic.wav")
magic_fx.set_volume(0.75)

#load background image
bg_image = pygame.image.load("assets/images/background/background.jpg").convert_alpha()

#load spritesheets
warrior_sheet = pygame.image.load("assets/images/warrior/Sprites/warrior.png").convert_alpha()
wizard_sheet = pygame.image.load("assets/images/wizard/Sprites/wizard.png").convert_alpha()

#load vicory image
victory_img = pygame.image.load("assets/images/icons/victory.png").convert_alpha()

#define number of steps in each animation
WARRIOR_ANIMATION_STEPS = [10, 8, 1, 7, 7, 3, 7]
WIZARD_ANIMATION_STEPS = [8, 8, 1, 8, 8, 3, 7]

#define font
count_font = pygame.font.Font("assets/fonts/turok.ttf", 80)
score_font = pygame.font.Font("assets/fonts/turok.ttf", 30)
game_over_font = pygame.font.Font("assets/fonts/turok.ttf", 50)
controls_font = pygame.font.Font("assets/fonts/turok.ttf", 25)
title_font = pygame.font.Font("assets/fonts/turok.ttf", 40)

#function for drawing text
def draw_text(text, font, text_col, x, y):
  img = font.render(text, True, text_col)
  screen.blit(img, (x, y))

#function for drawing background
def draw_bg():
  scaled_bg = pygame.transform.scale(bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
  screen.blit(scaled_bg, (0, 0))

#function for drawing fighter health bars
def draw_health_bar(health, x, y):
  ratio = health / 100
  pygame.draw.rect(screen, WHITE, (x - 2, y - 2, 404, 34))
  pygame.draw.rect(screen, RED, (x, y, 400, 30))
  pygame.draw.rect(screen, YELLOW, (x, y, 400 * ratio, 30))

#function to draw controls screen
def draw_controls_screen():
  # Vẽ nền tối mờ
  s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
  s.set_alpha(220)
  s.fill(BLACK)
  screen.blit(s, (0, 0))
  
  # Vẽ tiêu đề
  draw_text("HƯỚNG DẪN ĐIỀU KHIỂN", title_font, YELLOW, SCREEN_WIDTH // 2 - 220, 50)
  
  # Vẽ khung cho hướng dẫn người chơi 1
  pygame.draw.rect(screen, BLUE, (50, 120, 400, 350), 0)
  pygame.draw.rect(screen, WHITE, (50, 120, 400, 350), 3)
  
  # Vẽ hướng dẫn người chơi 1
  draw_text("NGƯỜI CHƠI 1 (WARRIOR)", controls_font, WHITE, 75, 130)
  draw_text("Di chuyển trái:    A", controls_font, WHITE, 75, 180)
  draw_text("Di chuyển phải:    D", controls_font, WHITE, 75, 220)
  draw_text("Nhảy:              W", controls_font, WHITE, 75, 260)
  draw_text("Tấn công 1:        R", controls_font, WHITE, 75, 300)
  draw_text("Tấn công 2:        T", controls_font, WHITE, 75, 340)
  draw_text("Tấn công 3:        Y", controls_font, WHITE, 75, 380)
  
  # Vẽ khung cho hướng dẫn người chơi 2
  pygame.draw.rect(screen, RED, (550, 120, 400, 350), 0)
  pygame.draw.rect(screen, WHITE, (550, 120, 400, 350), 3)
  
  # Vẽ hướng dẫn người chơi 2
  draw_text("NGƯỜI CHƠI 2 (WIZARD)", controls_font, WHITE, 575, 130)
  draw_text("Di chuyển trái:    ←", controls_font, WHITE, 575, 180)
  draw_text("Di chuyển phải:    →", controls_font, WHITE, 575, 220)
  draw_text("Nhảy:              ↑", controls_font, WHITE, 575, 260)
  draw_text("Tấn công 1:        J", controls_font, WHITE, 575, 300)
  draw_text("Tấn công 2:        K", controls_font, WHITE, 575, 340)
  draw_text("Tấn công 3:        L", controls_font, WHITE, 575, 380)
  
  # Hiển thị thông báo để bắt đầu
  draw_text("Nhấn SPACEBAR để bắt đầu trò chơi", controls_font, GREEN, SCREEN_WIDTH // 2 - 200, 500)

#function to reset game
def reset_game():
  global game_over, round_over, intro_count, score, winner
  game_over = False
  round_over = False
  intro_count = 5
  score = [0, 0]
  winner = 0
  return Fighter(1, 200, 310, False, WARRIOR_DATA, warrior_sheet, WARRIOR_ANIMATION_STEPS, sword_fx), Fighter(2, 700, 310, True, WIZARD_DATA, wizard_sheet, WIZARD_ANIMATION_STEPS, magic_fx)

#create two instances of fighters
fighter_1 = Fighter(1, 200, 310, False, WARRIOR_DATA, warrior_sheet, WARRIOR_ANIMATION_STEPS, sword_fx)
fighter_2 = Fighter(2, 700, 310, True, WIZARD_DATA, wizard_sheet, WIZARD_ANIMATION_STEPS, magic_fx)

#game loop
run = True
while run:

  clock.tick(FPS)

  #draw background
  draw_bg()

  if show_controls:
    # Hiển thị màn hình hướng dẫn
    draw_controls_screen()
    # Kiểm tra nếu người chơi nhấn phím SPACE để bắt đầu trò chơi
    key = pygame.key.get_pressed()
    if key[pygame.K_SPACE]:
      show_controls = False
  else:
    #show player stats
    draw_health_bar(fighter_1.health, 20, 20)
    draw_health_bar(fighter_2.health, 580, 20)
    draw_text("P1: " + str(score[0]), score_font, RED, 20, 60)
    draw_text("P2: " + str(score[1]), score_font, RED, 580, 60)

    #check if game is over
    if game_over:
      #display game over screen
      draw_text(f"PLAYER {winner} WINS!", game_over_font, BLUE, SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 100)
      draw_text("Press ENTER to play again", score_font, WHITE, SCREEN_WIDTH // 2 - 160, SCREEN_HEIGHT // 2)
      #check for key press to restart game
      key = pygame.key.get_pressed()
      if key[pygame.K_RETURN]:
        fighter_1, fighter_2 = reset_game()
        # Hiển thị lại màn hình hướng dẫn sau khi reset game
        show_controls = True
    elif intro_count <= 0:
      #move fighters if game is not over
      fighter_1.move(SCREEN_WIDTH, SCREEN_HEIGHT, screen, fighter_2, round_over)
      fighter_2.move(SCREEN_WIDTH, SCREEN_HEIGHT, screen, fighter_1, round_over)
    else:
      #display count timer
      draw_text(str(intro_count), count_font, RED, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 3)
      #update count timer
      if (pygame.time.get_ticks() - last_count_update) >= 1000:
        intro_count -= 1
        last_count_update = pygame.time.get_ticks()

    #update fighters
    fighter_1.update()
    fighter_2.update()

    #draw fighters
    fighter_1.draw(screen)
    fighter_2.draw(screen)

    #check for player defeat
    if not game_over:
      if round_over == False:
        if fighter_1.alive == False:
          score[1] += 1
          round_over = True
          round_over_time = pygame.time.get_ticks()
          #check if player 2 has won the game
          if score[1] >= WIN_SCORE:
            game_over = True
            winner = 2
        elif fighter_2.alive == False:
          score[0] += 1
          round_over = True
          round_over_time = pygame.time.get_ticks()
          #check if player 1 has won the game
          if score[0] >= WIN_SCORE:
            game_over = True
            winner = 1
      else:
        #display victory image for the round
        screen.blit(victory_img, (360, 150))
        if pygame.time.get_ticks() - round_over_time > ROUND_OVER_COOLDOWN and not game_over:
          round_over = False
          intro_count = 5
          fighter_1 = Fighter(1, 200, 310, False, WARRIOR_DATA, warrior_sheet, WARRIOR_ANIMATION_STEPS, sword_fx)
          fighter_2 = Fighter(2, 700, 310, True, WIZARD_DATA, wizard_sheet, WIZARD_ANIMATION_STEPS, magic_fx)

  #event handler
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      run = False

  #update display
  pygame.display.update()

#exit pygame
pygame.quit()