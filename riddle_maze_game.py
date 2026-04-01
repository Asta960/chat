#!/usr/bin/env python3
"""
Бесконечная игра-лабиринт со Сфинксом и обучающимся ИИ.
ИИ обучается в реальном времени, видит только поле зрения, графика на Pygame.

Управление:
- Стрелки: перемещение (в режиме игры за человека)
- R: перезапуск уровня
- Q: выход
- L: переключение режима (Человек / Наблюдение за ИИ)

Особенности:
- Процедурная генерация лабиринта
- Сфинкс появляется случайно и задает загадку
- 4 выхода соответствуют 4 направлениям (Лево-Верх, Право-Верх, Лево-Низ, Право-Низ)
- ИИ использует Q-learning с ограниченным полем зрения
- Обучение в реальном времени без пауз
"""

import pygame
import random
import math
import json
import os
import sys
import time
from collections import defaultdict
from enum import Enum

# Проверка доступности графического интерфейса
USE_PYGAME = False
try:
    # Принудительно используем dummy драйвер для headless окружения
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['DISPLAY'] = ''
    
    pygame.init()
    USE_PYGAME = True
except Exception as e:
    print(f"Графический интерфейс недоступен ({e}). Запуск в текстовом режиме (ASCII).")
    USE_PYGAME = False

if USE_PYGAME:
    # Константы для графики
    TILE_SIZE = 40
    MAZE_WIDTH = 21  # Нечетное число для алгоритма генерации
    MAZE_HEIGHT = 21
    SCREEN_WIDTH = MAZE_WIDTH * TILE_SIZE
    SCREEN_HEIGHT = MAZE_HEIGHT * TILE_SIZE + 100  # Место для интерфейса
    FPS = 60
    
    # Цвета
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (128, 128, 128)
    DARK_GRAY = (64, 64, 64)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    PURPLE = (128, 0, 128)
    ORANGE = (255, 165, 0)
    CYAN = (0, 255, 255)
else:
    # Константы для текстового режима
    FPS = 5  # Скорость обновления в текстовом режиме
    TILE_SIZE = 1
    MAZE_WIDTH = 21
    MAZE_HEIGHT = 21

class Direction(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

class MazeGenerator:
    """Генератор лабиринтов с использованием алгоритма Recursive Backtracker"""
    
    @staticmethod
    def generate(width, height):
        if width % 2 == 0:
            width += 1
        if height % 2 == 0:
            height += 1
            
        maze = [[1 for _ in range(width)] for _ in range(height)]
        
        def carve(x, y):
            maze[y][x] = 0
            directions = [(0, -2), (0, 2), (-2, 0), (2, 0)]
            random.shuffle(directions)
            
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 0 < nx < width - 1 and 0 < ny < height - 1 and maze[ny][nx] == 1:
                    maze[y + dy // 2][x + dx // 2] = 0
                    carve(nx, ny)
        
        start_x, start_y = 1, 1
        carve(start_x, start_y)
        
        # Добавляем несколько дополнительных проходов для разнообразия
        for _ in range(random.randint(3, 7)):
            x = random.randrange(1, width - 1)
            y = random.randrange(1, height - 1)
            if maze[y][x] == 1:
                # Проверяем соседей
                neighbors = []
                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and maze[ny][nx] == 0:
                        neighbors.append((dx, dy))
                
                if len(neighbors) >= 2:
                    maze[y][x] = 0
        
        return maze
    
    @staticmethod
    def find_empty_positions(maze, count=1):
        positions = []
        height = len(maze)
        width = len(maze[0])
        
        empty_cells = []
        for y in range(height):
            for x in range(width):
                if maze[y][x] == 0:
                    empty_cells.append((x, y))
        
        if len(empty_cells) < count:
            return empty_cells
        
        return random.sample(empty_cells, count)


class RiddleSystem:
    """Система загадок Сфинкса"""
    
    def __init__(self):
        self.riddles = [
            {
                "question": "Что имеет ключи, но не может открыть ни одного замка?",
                "answer": 0,  # Лево-Верх
                "options": ["Пианино", "Карта", "Код", "Сейф"]
            },
            {
                "question": "Что становится больше, если от него отнять?",
                "answer": 1,  # Право-Верх
                "options": ["Долг", "Яма", "Возраст", "Тень"]
            },
            {
                "question": "Что всегда идет, но никогда не двигается с места?",
                "answer": 2,  # Лево-Низ
                "options": ["Река", "Время", "Дорога", "Часы"]
            },
            {
                "question": "У чего есть глаза, но не видно?",
                "answer": 3,  # Право-Низ
                "options": ["Картошка", "Игла", "Шторм", "Зеркало"]
            },
            {
                "question": "Что можно разбить, только назвав?",
                "answer": 0,
                "options": ["Тишину", "Лёд", "Мечту", "Обещание"]
            },
            {
                "question": "Что принадлежит тебе, но другие используют это чаще?",
                "answer": 1,
                "options": ["Имя", "Деньги", "Машина", "Дом"]
            },
            {
                "question": "Чем больше ешь, тем больше становится?",
                "answer": 2,
                "options": ["Свинья", "Дыра", "Аппетит", "Куча"]
            },
            {
                "question": "Что имеет голову, но не имеет мозга?",
                "answer": 3,
                "options": ["Монета", "Гвоздь", "Цветок", "Книга"]
            },
            {
                "question": "Что может путешествовать по миру, оставаясь в углу?",
                "answer": 0,
                "options": ["Марка", "Мысль", "Паук", "Тень"]
            },
            {
                "question": "У кого одна нога, но тот не ходит?",
                "answer": 1,
                "options": ["Стол", "Гриб", "Флаг", "Дерево"]
            }
        ]
    
    def get_random_riddle(self):
        return random.choice(self.riddles)
    
    def get_direction_from_answer(self, answer_idx):
        """Преобразует индекс ответа в направление движения"""
        # 0: Лево-Верх, 1: Право-Верх, 2: Лево-Низ, 3: Право-Низ
        mapping = {
            0: (Direction.LEFT, Direction.UP),
            1: (Direction.RIGHT, Direction.UP),
            2: (Direction.LEFT, Direction.DOWN),
            3: (Direction.RIGHT, Direction.DOWN)
        }
        return mapping[answer_idx]


class VisionSystem:
    """Система поля зрения для ИИ"""
    
    @staticmethod
    def get_visible_area(maze, player_x, player_y, radius=5):
        """
        Возвращает видимую область вокруг игрока.
        ИИ не видит сквозь стены - используется raycasting.
        """
        height = len(maze)
        width = len(maze[0])
        visible = [[None for _ in range(width)] for _ in range(height)]
        
        for angle in range(0, 360, 2):  # Проверка каждые 2 градуса
            rad = math.radians(angle)
            dx = math.cos(rad)
            dy = math.sin(rad)
            
            # Ray casting
            for dist in range(radius * 2):
                x = int(player_x + dx * dist)
                y = int(player_y + dy * dist)
                
                if x < 0 or x >= width or y < 0 or y >= height:
                    break
                
                visible[y][x] = maze[y][x]
                
                if maze[y][x] == 1:  # Стена блокирует обзор
                    break
        
        return visible
    
    @staticmethod
    def get_vision_state(maze, player_x, player_y, radius=5):
        """
        Создает компактное представление состояния для ИИ на основе видимой области.
        Возвращает хешируемое состояние.
        """
        visible = VisionSystem.get_visible_area(maze, player_x, player_y, radius)
        
        # Создаем упрощенное представление: расстояние до стен в 8 направлениях
        directions = [
            (0, -1), (1, -1), (1, 0), (1, 1),
            (0, 1), (-1, 1), (-1, 0), (-1, -1)
        ]
        
        state = []
        for dx, dy in directions:
            dist = 0
            x, y = player_x, player_y
            for _ in range(radius):
                x += dx
                y += dy
                if x < 0 or x >= len(maze[0]) or y < 0 or y >= len(maze):
                    dist += 1
                    break
                if visible[y][x] == 1 or visible[y][x] is None:
                    dist += 1
                    break
                dist += 1
            state.append(min(dist, radius))
        
        return tuple(state)


class QLearningAI:
    """ИИ на базе Q-learning"""
    
    def __init__(self, alpha=0.1, gamma=0.95, epsilon=1.0, epsilon_decay=0.995, epsilon_min=0.05):
        self.q_table = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # 4 действия
        self.alpha = alpha  # Скорость обучения
        self.gamma = gamma  # Дисконтный фактор
        self.epsilon = epsilon  # Исследование
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.actions = [Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT]
        self.model_file = "ai_maze_model.json"
    
    def get_action(self, state, training=True):
        """Выбор действия на основе политики epsilon-greedy"""
        if training and random.random() < self.epsilon:
            return random.choice(self.actions)
        
        q_values = self.q_table[state]
        max_q = max(q_values)
        best_actions = [i for i, q in enumerate(q_values) if q == max_q]
        return self.actions[random.choice(best_actions)]
    
    def update(self, state, action, reward, next_state, done):
        """Обновление Q-таблицы"""
        action_idx = self.actions.index(action)
        
        if done:
            target = reward
        else:
            next_q_values = self.q_table[next_state]
            target = reward + self.gamma * max(next_q_values)
        
        current_q = self.q_table[state][action_idx]
        self.q_table[state][action_idx] += self.alpha * (target - current_q)
    
    def decay_epsilon(self):
        """Уменьшение коэффициента исследования"""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
    
    def save_model(self):
        """Сохранение модели в файл"""
        model_data = {
            'q_table': {str(k): v for k, v in self.q_table.items()},
            'epsilon': self.epsilon
        }
        with open(self.model_file, 'w') as f:
            json.dump(model_data, f)
        print(f"Модель сохранена в {self.model_file}")
    
    def load_model(self):
        """Загрузка модели из файла"""
        if os.path.exists(self.model_file):
            try:
                with open(self.model_file, 'r') as f:
                    model_data = json.load(f)
                self.q_table = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0], 
                                          {eval(k): v for k, v in model_data['q_table'].items()})
                self.epsilon = model_data.get('epsilon', self.epsilon_min)
                print(f"Модель загружена из {self.model_file}")
                return True
            except Exception as e:
                print(f"Ошибка загрузки модели: {e}")
        return False


class Game:
    """Основной класс игры"""
    
    def __init__(self):
        if USE_PYGAME:
            pygame.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("Лабиринт Сфинкса - Обучающийся ИИ")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 18)
        else:
            self.screen = None
            self.clock = None
            self.font = None
            self.small_font = None
        
        self.maze_generator = MazeGenerator()
        self.riddle_system = RiddleSystem()
        self.vision_system = VisionSystem()
        self.ai = QLearningAI()
        
        self.reset_game()
        
        # Режимы: 'human', 'ai_train', 'ai_watch'
        self.mode = 'ai_train'
        self.training_episodes = 0
        self.successful_episodes = 0
        
        # Для анимации
        self.animation_timer = 0
        self.message_timer = 0
        self.current_message = ""
        
        # Загрузка существующей модели
        self.ai.load_model()
    
    def reset_game(self):
        """Сброс и генерация нового уровня"""
        self.maze = self.maze_generator.generate(MAZE_WIDTH, MAZE_HEIGHT)
        
        # Позиция игрока
        empty_positions = self.maze_generator.find_empty_positions(self.maze, 2)
        self.player_x, self.player_y = empty_positions[0]
        self.start_x, self.start_y = self.player_x, self.player_y
        
        # Позиция Сфинкса
        self.sphinx_x, self.sphinx_y = empty_positions[1]
        
        # Текущая загадка
        self.current_riddle = self.riddle_system.get_random_riddle()
        self.riddle_active = True
        self.riddle_solved = False
        self.game_over = False
        self.win = False
        
        # Статистика уровня
        self.moves = 0
        self.episode_reward = 0
    
    def get_state(self):
        """Получение текущего состояния для ИИ"""
        vision_state = self.vision_system.get_vision_state(
            self.maze, self.player_x, self.player_y
        )
        
        # Добавляем информацию о наличии Сфинкса в поле зрения
        sphinx_visible = abs(self.player_x - self.sphinx_x) <= 5 and abs(self.player_y - self.sphinx_y) <= 5
        riddle_state = 0
        if self.riddle_active:
            riddle_state = 1 if sphinx_visible else 2
        
        return (vision_state, riddle_state)
    
    def move_player(self, direction):
        """Перемещение игрока"""
        dx, dy = 0, 0
        if direction == Direction.UP:
            dy = -1
        elif direction == Direction.DOWN:
            dy = 1
        elif direction == Direction.LEFT:
            dx = -1
        elif direction == Direction.RIGHT:
            dx = 1
        
        new_x = self.player_x + dx
        new_y = self.player_y + dy
        
        if 0 <= new_x < len(self.maze[0]) and 0 <= new_y < len(self.maze):
            if self.maze[new_y][new_x] == 0:
                self.player_x = new_x
                self.player_y = new_y
                self.moves += 1
                return True
        return False
    
    def check_sphinx_encounter(self):
        """Проверка встречи со Сфинксом"""
        if self.player_x == self.sphinx_x and self.player_y == self.sphinx_y:
            if self.riddle_active and not self.riddle_solved:
                return True
        return False
    
    def solve_riddle(self, choice):
        """
        Попытка решить загадку.
        choice: 0=Лево-Верх, 1=Право-Верх, 2=Лево-Низ, 3=Право-Низ
        """
        if choice == self.current_riddle["answer"]:
            self.riddle_solved = True
            self.riddle_active = False
            self.win = True
            self.current_message = "Загадка решена! Новый уровень..."
            self.message_timer = 60
            return True
        else:
            self.game_over = True
            self.current_message = f"Неправильно! Правильный ответ: {self.current_riddle['options'][self.current_riddle['answer']]}"
            self.message_timer = 120
            return False
    
    def update_ai(self):
        """Обучение ИИ в реальном времени"""
        if self.mode != 'ai_train' and self.mode != 'ai_watch':
            return
        
        state = self.get_state()
        action = self.ai.get_action(state, training=(self.mode == 'ai_train'))
        
        # Выполнение действия
        old_state = state
        moved = self.move_player(action)
        
        # Расчет награды
        reward = -0.1  # Небольшой штраф за каждый ход (чтобы искал кратчайший путь)
        done = False
        
        if not moved:
            reward = -0.5  # Штраф за попытку идти в стену
        
        # Проверка встречи со Сфинксом
        if self.check_sphinx_encounter():
            # ИИ должен выбрать ответ (случайно или на основе обучения)
            if self.mode == 'ai_train':
                # Для простоты: ИИ выбирает случайный ответ во время обучения
                # В более сложной версии можно обучать выбору ответов
                choice = random.randint(0, 3)
            else:
                choice = random.randint(0, 3)
            
            if self.solve_riddle(choice):
                reward = 10.0  # Большая награда за победу
                done = True
            else:
                reward = -10.0  # Большой штраф за проигрыш
                done = True
        
        # Проверка победы (если загадка уже решена в предыдущих уровнях)
        if self.win:
            done = True
        
        # Получение нового состояния
        new_state = self.get_state()
        
        # Обновление Q-таблицы
        if self.mode == 'ai_train':
            self.ai.update(old_state, action, reward, new_state, done)
            self.ai.decay_epsilon()
        
        self.episode_reward += reward
        
        # Если эпизод завершен
        if done or self.game_over:
            self.training_episodes += 1
            if self.win:
                self.successful_episodes += 1
            
            # Автоматический сброс через небольшую паузу
            if self.message_timer <= 0:
                self.reset_game()
        
        return action
    
    def draw_maze(self, visible_area=None):
        """Отрисовка лабиринта"""
        for y in range(len(self.maze)):
            for x in range(len(self.maze[0])):
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                
                # Проверка видимости
                is_visible = True
                if visible_area:
                    is_visible = visible_area[y][x] is not None
                
                if not is_visible:
                    color = BLACK
                elif self.maze[y][x] == 1:
                    color = DARK_GRAY
                else:
                    color = BLACK
                
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, GRAY, rect, 1)
    
    def draw_entities(self):
        """Отрисовка игрока и Сфинкса"""
        # Игрок
        player_rect = pygame.Rect(
            self.player_x * TILE_SIZE + 5,
            self.player_y * TILE_SIZE + 5,
            TILE_SIZE - 10,
            TILE_SIZE - 10
        )
        pygame.draw.rect(self.screen, BLUE, player_rect)
        pygame.draw.rect(self.screen, WHITE, player_rect, 2)
        
        # Сфинкс
        if self.riddle_active:
            sphinx_rect = pygame.Rect(
                self.sphinx_x * TILE_SIZE + 5,
                self.sphinx_y * TILE_SIZE + 5,
                TILE_SIZE - 10,
                TILE_SIZE - 10
            )
            pygame.draw.rect(self.screen, ORANGE, sphinx_rect)
            pygame.draw.circle(self.screen, YELLOW, 
                             (self.sphinx_x * TILE_SIZE + TILE_SIZE // 2,
                              self.sphinx_y * TILE_SIZE + TILE_SIZE // 2),
                             5)
    
    def draw_interface(self):
        """Отрисовка интерфейса"""
        interface_y = MAZE_HEIGHT * TILE_SIZE
        pygame.draw.rect(self.screen, DARK_GRAY, (0, interface_y, SCREEN_WIDTH, 100))
        
        # Информация о режиме
        mode_text = f"Режим: {'Обучение ИИ' if self.mode == 'ai_train' else 'Наблюдение' if self.mode == 'ai_watch' else 'Человек'}"
        text_surface = self.font.render(mode_text, True, WHITE)
        self.screen.blit(text_surface, (10, interface_y + 10))
        
        # Статистика обучения
        stats_text = f"Эпизоды: {self.training_episodes} | Успехи: {self.successful_episodes}"
        if self.training_episodes > 0:
            win_rate = (self.successful_episodes / self.training_episodes) * 100
            stats_text += f" | Win Rate: {win_rate:.1f}%"
        text_surface = self.font.render(stats_text, True, WHITE)
        self.screen.blit(text_surface, (10, interface_y + 35))
        
        # Epsilon
        eps_text = f"Epsilon: {self.ai.epsilon:.3f}"
        text_surface = self.small_font.render(eps_text, True, CYAN)
        self.screen.blit(text_surface, (10, interface_y + 60))
        
        # Текущая загадка (если активна)
        if self.riddle_active and self.message_timer <= 0:
            riddle_text = f"Загадка: {self.current_riddle['question']}"
            text_surface = self.small_font.render(riddle_text, True, YELLOW)
            self.screen.blit(text_surface, (200, interface_y + 10))
            
            options_text = "Выходы: 0=Лево-Верх, 1=Право-Верх, 2=Лево-Низ, 3=Право-Низ"
            text_surface = self.small_font.render(options_text, True, WHITE)
            self.screen.blit(text_surface, (200, interface_y + 30))
        
        # Сообщение
        if self.message_timer > 0:
            msg_surface = self.font.render(self.current_message, True, GREEN)
            self.screen.blit(msg_surface, (SCREEN_WIDTH // 2 - msg_surface.get_width() // 2, interface_y + 70))
            self.message_timer -= 1
        
        # Управление
        controls_text = "L-режим | R-рестарт | Q-выход | Стрелки-движение (человек)"
        text_surface = self.small_font.render(controls_text, True, GRAY)
        self.screen.blit(text_surface, (SCREEN_WIDTH - text_surface.get_width() - 10, interface_y + 60))
    
    def run(self):
        """Основной игровой цикл"""
        running = True
        auto_reset_timer = 0
        
        if not USE_PYGAME:
            # Текстовый режим
            print("\n=== Лабиринт Сфинкса (Текстовый режим) ===")
            print("Обучение ИИ запущено. Нажмите Ctrl+C для остановки.")
            
            try:
                while running:
                    # Обновление ИИ
                    if self.mode in ['ai_train', 'ai_watch']:
                        self.update_ai()
                    
                    # Авто-рестарт после победы/поражения
                    if self.win or self.game_over:
                        auto_reset_timer += 1
                        if auto_reset_timer > 2:  # Короткая пауза
                            if self.mode == 'ai_train':
                                print(f"Эпизод {self.training_episodes}: {'ПОБЕДА' if self.win else 'ПОРАЖЕНИЕ'} | Win Rate: {(self.successful_episodes/self.training_episodes)*100:.1f}%")
                            self.reset_game()
                            auto_reset_timer = 0
                    
                    time.sleep(1.0 / FPS)
                    
            except KeyboardInterrupt:
                print("\nОстановка обучения...")
                running = False
            
            # Сохранение модели при выходе
            self.ai.save_model()
            return
        
        # Графический режим (Pygame)
        while running:
            self.clock.tick(FPS)
            
            # Обработка событий
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                    
                    elif event.key == pygame.K_l:
                        modes = ['human', 'ai_train', 'ai_watch']
                        current_idx = modes.index(self.mode)
                        self.mode = modes[(current_idx + 1) % len(modes)]
                        if self.mode == 'ai_train':
                            self.reset_game()
                    
                    elif event.key == pygame.K_r:
                        self.reset_game()
                    
                    elif event.key == pygame.K_s:
                        self.ai.save_model()
                    
                    # Управление человеком
                    if self.mode == 'human':
                        if event.key == pygame.K_UP:
                            self.move_player(Direction.UP)
                        elif event.key == pygame.K_DOWN:
                            self.move_player(Direction.DOWN)
                        elif event.key == pygame.K_LEFT:
                            self.move_player(Direction.LEFT)
                        elif event.key == pygame.K_RIGHT:
                            self.move_player(Direction.RIGHT)
                        
                        # Проверка встречи со Сфинксом
                        if self.check_sphinx_encounter() and self.riddle_active:
                            # Для человека: показываем варианты и ждем ввода
                            pass  # В данной версии человек тоже выбирает случайно для простоты
            
            # Обновление ИИ
            if self.mode in ['ai_train', 'ai_watch']:
                self.update_ai()
            
            # Авто-рестарт после победы/поражения
            if self.win or self.game_over:
                auto_reset_timer += 1
                if auto_reset_timer > 60:  # 1 секунда пауза
                    self.reset_game()
                    auto_reset_timer = 0
            
            # Отрисовка
            self.screen.fill(BLACK)
            
            # Получение видимой области (для отображения)
            visible_area = self.vision_system.get_visible_area(
                self.maze, self.player_x, self.player_y, radius=5
            )
            
            self.draw_maze(visible_area)
            self.draw_entities()
            self.draw_interface()
            
            pygame.display.flip()
        
        # Сохранение модели при выходе
        self.ai.save_model()
        pygame.quit()


if __name__ == "__main__":
    print("Запуск игры 'Лабиринт Сфинкса'...")
    print("Режим по умолчанию: Обучение ИИ в реальном времени")
    print("Нажмите L для смены режима, Q для выхода")
    game = Game()
    game.run()
