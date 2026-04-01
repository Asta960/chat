import pygame
import random
import json
import os

# Инициализация Pygame
pygame.init()

# Константы
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
TILE_SIZE = 40
MAZE_WIDTH = 21
MAZE_HEIGHT = 21
FOV_RADIUS = 5
FPS = 30

# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
BLUE = (0, 100, 255)
ORANGE = (255, 165, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)

# Направления
UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

DIRECTIONS = {
    UP: (0, -1),
    RIGHT: (1, 0),
    DOWN: (0, 1),
    LEFT: (-1, 0)
}

DIRECTION_NAMES = {
    UP: "верхний",
    RIGHT: "правый", 
    DOWN: "нижний",
    LEFT: "левый"
}

class Maze:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[1 for _ in range(width)] for _ in range(height)]
        self.generate()
    
    def generate(self):
        stack = []
        start_x, start_y = 1, 1
        self.grid[start_y][start_x] = 0
        stack.append((start_x, start_y))
        
        while stack:
            x, y = stack[-1]
            neighbors = []
            for dx, dy in [(0, -2), (2, 0), (0, 2), (-2, 0)]:
                nx, ny = x + dx, y + dy
                if 0 < nx < self.width - 1 and 0 < ny < self.height - 1:
                    if self.grid[ny][nx] == 1:
                        neighbors.append((nx, ny, dx // 2, dy // 2))
            
            if neighbors:
                nx, ny, dx, dy = random.choice(neighbors)
                self.grid[y + dy][x + dx] = 0
                self.grid[ny][nx] = 0
                stack.append((nx, ny))
            else:
                stack.pop()
    
    def get_available_exits(self, x, y):
        exits = []
        for direction, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.grid[ny][nx] == 0:
                    exits.append(direction)
        return exits
    
    def is_wall(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True
        return self.grid[y][x] == 1

class Sphinx:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.riddle_given = False
        self.correct_exit = None
    
    def generate_riddle(self, available_exits):
        if not available_exits:
            return None, None
        self.correct_exit = random.choice(available_exits)
        riddle = f"Иди в {DIRECTION_NAMES[self.correct_exit]} проход"
        return riddle, self.correct_exit

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.known_map = {}
    
    def move(self, dx, dy, maze):
        new_x = self.x + dx
        new_y = self.y + dy
        if not maze.is_wall(new_x, new_y):
            self.x = new_x
            self.y = new_y
            self.update_known_map(maze)
            return True
        return False
    
    def update_known_map(self, maze):
        for dy in range(-FOV_RADIUS, FOV_RADIUS + 1):
            for dx in range(-FOV_RADIUS, FOV_RADIUS + 1):
                if dx * dx + dy * dy <= FOV_RADIUS * FOV_RADIUS:
                    world_x = self.x + dx
                    world_y = self.y + dy
                    if 0 <= world_x < maze.width and 0 <= world_y < maze.height:
                        if self.has_line_of_sight(world_x, world_y, maze):
                            self.known_map[(world_x, world_y)] = maze.grid[world_y][world_x]
    
    def has_line_of_sight(self, target_x, target_y, maze):
        dx = target_x - self.x
        dy = target_y - self.y
        distance = max(abs(dx), abs(dy))
        if distance == 0:
            return True
        step_x = dx / distance if dx != 0 else 0
        step_y = dy / distance if dy != 0 else 0
        x, y = float(self.x), float(self.y)
        for _ in range(int(distance)):
            x += step_x
            y += step_y
            check_x, check_y = int(round(x)), int(round(y))
            if maze.is_wall(check_x, check_y):
                return False
        return True
    
    def can_see(self, x, y):
        return (x, y) in self.known_map

class AI:
    def __init__(self):
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.1
    
    def get_state(self, player, sphinx, maze):
        visible_walls = []
        for dy in range(-FOV_RADIUS, FOV_RADIUS + 1):
            for dx in range(-FOV_RADIUS, FOV_RADIUS + 1):
                if dx * dx + dy * dy <= FOV_RADIUS * FOV_RADIUS:
                    world_x = player.x + dx
                    world_y = player.y + dy
                    if player.can_see(world_x, world_y):
                        is_wall = maze.is_wall(world_x, world_y)
                        visible_walls.append((dx, dy, is_wall))
        
        sphinx_visible = player.can_see(sphinx.x, sphinx.y)
        sphinx_dir = None
        if sphinx_visible:
            dx = sphinx.x - player.x
            dy = sphinx.y - player.y
            if abs(dx) > abs(dy):
                sphinx_dir = RIGHT if dx > 0 else LEFT
            else:
                sphinx_dir = DOWN if dy > 0 else UP
        
        riddle_info = sphinx.correct_exit if sphinx.riddle_given else None
        state = (tuple(sorted(visible_walls)), sphinx_dir, riddle_info)
        return state
    
    def get_action(self, state, available_actions):
        if random.random() < self.epsilon or state not in self.q_table:
            return random.choice(available_actions)
        q_values = self.q_table.get(state, {})
        best_action = max(available_actions, key=lambda a: q_values.get(a, 0))
        return best_action
    
    def update(self, state, action, reward, next_state, available_actions):
        if state not in self.q_table:
            self.q_table[state] = {}
        old_q = self.q_table[state].get(action, 0)
        if next_state in self.q_table and self.q_table[next_state]:
            max_next_q = max(self.q_table[next_state].get(a, 0) for a in available_actions)
        else:
            max_next_q = 0
        new_q = old_q + self.learning_rate * (reward + self.discount_factor * max_next_q - old_q)
        self.q_table[state][action] = new_q
    
    def save(self, filename="ai_model.json"):
        serializable_q_table = {}
        for state, actions in self.q_table.items():
            state_key = str(state)
            serializable_q_table[state_key] = actions
        with open(filename, 'w') as f:
            json.dump(serializable_q_table, f)
    
    def load(self, filename="ai_model.json"):
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r') as f:
                serializable_q_table = json.load(f)
            self.q_table = {}
            for state_key, actions in serializable_q_table.items():
                state = eval(state_key)
                self.q_table[state] = actions
            return True
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            return False

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Лабиринт Сфинкса - ИИ Обучение")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.ai = AI()
        self.mode = "TRAIN"
        self.running = True
        self.level = 1
        self.score = 0
        self.total_games = 0
        self.wins = 0
        
        self.reset_level()
    
    def reset_level(self):
        self.maze = Maze(MAZE_WIDTH, MAZE_HEIGHT)
        free_positions = []
        for y in range(1, MAZE_HEIGHT - 1, 2):
            for x in range(1, MAZE_WIDTH - 1, 2):
                if self.maze.grid[y][x] == 0:
                    free_positions.append((x, y))
        
        if len(free_positions) < 2:
            free_positions = [(1, 1), (3, 3)]
        
        random.shuffle(free_positions)
        player_pos = free_positions[0]
        sphinx_pos = free_positions[1]
        
        self.player = Player(player_pos[0], player_pos[1])
        self.sphinx = Sphinx(sphinx_pos[0], sphinx_pos[1])
        
        exits = self.maze.get_available_exits(self.sphinx.x, self.sphinx.y)
        if exits:
            self.riddle, self.correct_exit = self.sphinx.generate_riddle(exits)
            self.sphinx.riddle_given = True
        else:
            self.riddle = "Нет доступных выходов"
            self.correct_exit = None
        
        self.game_over = False
        self.message = ""
        self.message_timer = 0
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    self.running = False
                elif event.key == pygame.K_l:
                    modes = ["TRAIN", "WATCH", "PLAY"]
                    current_idx = modes.index(self.mode)
                    self.mode = modes[(current_idx + 1) % len(modes)]
                elif event.key == pygame.K_r:
                    self.reset_level()
                elif event.key == pygame.K_s:
                    self.ai.save()
                    self.show_message("Модель сохранена!")
                elif event.key == pygame.K_o:
                    if self.ai.load():
                        self.show_message("Модель загружена!")
                    else:
                        self.show_message("Нет сохраненной модели")
                
                if self.mode == "PLAY" and not self.game_over:
                    dx, dy = 0, 0
                    if event.key == pygame.K_UP:
                        dy = -1
                    elif event.key == pygame.K_DOWN:
                        dy = 1
                    elif event.key == pygame.K_LEFT:
                        dx = -1
                    elif event.key == pygame.K_RIGHT:
                        dx = 1
                    
                    if dx != 0 or dy != 0:
                        self.player.move(dx, dy, self.maze)
                        self.check_win_condition()
    
    def show_message(self, text, duration=120):
        self.message = text
        self.message_timer = duration
    
    def update_ai(self):
        if self.mode not in ["TRAIN", "WATCH"]:
            return
        if self.game_over:
            return
        
        state = self.ai.get_state(self.player, self.sphinx, self.maze)
        available_actions = list(DIRECTIONS.keys())
        action = self.ai.get_action(state, available_actions)
        
        dx, dy = DIRECTIONS[action]
        moved = self.player.move(dx, dy, self.maze)
        
        reward = -0.1
        if not moved:
            reward = -0.5
        
        self.check_win_condition()
        
        next_state = self.ai.get_state(self.player, self.sphinx, self.maze)
        next_available_actions = list(DIRECTIONS.keys())
        self.ai.update(state, action, reward, next_state, next_available_actions)
    
    def check_win_condition(self):
        if self.game_over:
            return
        
        dx = abs(self.player.x - self.sphinx.x)
        dy = abs(self.player.y - self.sphinx.y)
        
        if dx + dy == 1:
            if self.player.x < self.sphinx.x:
                player_side = LEFT
            elif self.player.x > self.sphinx.x:
                player_side = RIGHT
            elif self.player.y < self.sphinx.y:
                player_side = UP
            else:
                player_side = DOWN
            
            if player_side == self.correct_exit:
                self.game_over = True
                self.wins += 1
                self.score += 10
                self.show_message("Победа! Правильный выход!", 180)
                
                state = self.ai.get_state(self.player, self.sphinx, self.maze)
                self.ai.q_table.setdefault(state, {})
                for action in DIRECTIONS:
                    if action == player_side:
                        self.ai.q_table[state][action] = self.ai.q_table[state].get(action, 0) + 10
            else:
                self.game_over = True
                self.score -= 5
                self.show_message("Неверный выход!", 180)
                
                state = self.ai.get_state(self.player, self.sphinx, self.maze)
                self.ai.q_table.setdefault(state, {})
                for action in DIRECTIONS:
                    if action == player_side:
                        self.ai.q_table[state][action] = self.ai.q_table[state].get(action, 0) - 5
            
            self.total_games += 1
            
            if self.mode in ["TRAIN", "WATCH"]:
                pygame.time.set_timer(pygame.USEREVENT, 1000)
    
    def draw(self):
        self.screen.fill(BLACK)
        
        camera_x = self.player.x * TILE_SIZE - WINDOW_WIDTH // 2
        camera_y = self.player.y * TILE_SIZE - WINDOW_HEIGHT // 2
        
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                if self.player.can_see(x, y):
                    color = WHITE if self.maze.grid[y][x] == 1 else DARK_GRAY
                elif (x, y) in self.player.known_map:
                    color = GRAY if self.player.known_map[(x, y)] == 1 else (80, 80, 80)
                else:
                    continue
                
                rect = pygame.Rect(
                    x * TILE_SIZE - camera_x,
                    y * TILE_SIZE - camera_y,
                    TILE_SIZE,
                    TILE_SIZE
                )
                pygame.draw.rect(self.screen, color, rect)
        
        sphinx_rect = pygame.Rect(
            self.sphinx.x * TILE_SIZE - camera_x,
            self.sphinx.y * TILE_SIZE - camera_y,
            TILE_SIZE,
            TILE_SIZE
        )
        pygame.draw.rect(self.screen, ORANGE, sphinx_rect)
        pygame.draw.circle(self.screen, YELLOW, 
                          (sphinx_rect.centerx, sphinx_rect.centery), 
                          TILE_SIZE // 4)
        
        player_rect = pygame.Rect(
            self.player.x * TILE_SIZE - camera_x,
            self.player.y * TILE_SIZE - camera_y,
            TILE_SIZE,
            TILE_SIZE
        )
        pygame.draw.rect(self.screen, BLUE, player_rect)
        
        self.draw_ui()
        pygame.display.flip()
    
    def draw_ui(self):
        mode_text = f"Режим: {self.mode}"
        mode_surface = self.font.render(mode_text, True, WHITE)
        self.screen.blit(mode_surface, (10, 10))
        
        score_text = f"Уровень: {self.level} | Счет: {self.score} | Победы: {self.wins}/{self.total_games}"
        score_surface = self.small_font.render(score_text, True, WHITE)
        self.screen.blit(score_surface, (10, 50))
        
        if self.riddle:
            riddle_text = f"Сфинкс: {self.riddle}"
            riddle_surface = self.small_font.render(riddle_text, True, YELLOW)
            self.screen.blit(riddle_surface, (10, 80))
        
        if self.message_timer > 0:
            message_surface = self.font.render(self.message, True, GREEN)
            self.screen.blit(message_surface, 
                           (WINDOW_WIDTH // 2 - message_surface.get_width() // 2, 
                            WINDOW_HEIGHT - 100))
            self.message_timer -= 1
        
        hints = [
            "L - смена режима",
            "R - рестарт", 
            "S - сохранить модель",
            "O - загрузить модель",
            "Q - выход",
            "Стрелки - движение (PLAY)"
        ]
        
        for i, hint in enumerate(hints):
            hint_surface = self.small_font.render(hint, True, GRAY)
            self.screen.blit(hint_surface, (WINDOW_WIDTH - 200, 10 + i * 25))
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update_ai()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
