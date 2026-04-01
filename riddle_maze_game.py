#!/usr/bin/env python3
"""
Лабиринт со Сфинксом - бесконечная игра с обучающимся ИИ.
ИИ исследует лабиринт, находит Сфинкса, отгадывает загадки и выбирает правильные выходы.
Используется Q-learning для обучения.
"""

import random
import os
import time
import json
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Константы
CELL_WALL = '#'
CELL_PATH = '.'
CELL_PLAYER = 'P'
CELL_SPHINX = 'S'
CELL_EXIT = 'E'
CELL_VISITED = '*'

DIRECTIONS = {
    'up': (-1, 0),
    'down': (1, 0),
    'left': (0, -1),
    'right': (0, 1)
}

DIRECTION_SYMBOLS = {
    'up': '↑',
    'down': '↓',
    'left': '←',
    'right': '→'
}


class Riddle:
    """Класс загадки Сфинкса"""
    
    def __init__(self):
        self.riddles = [
            {
                "question": "Что имеет ноги, но не ходит?",
                "answer": "стул",
                "alternatives": ["стол", "кровать", "шкаф"]
            },
            {
                "question": "Чем больше берешь, тем больше становится?",
                "answer": "яма",
                "alternatives": ["долг", "снег", "огонь"]
            },
            {
                "question": "Что можно разбить, даже не трогая?",
                "answer": "обещание",
                "alternatives": ["стекло", "зеркало", "сердце"]
            },
            {
                "question": "Что всегда идет, но никогда не движется?",
                "answer": "время",
                "alternatives": ["часы", "река", "дорога"]
            },
            {
                "question": "У чего есть глаза, но не видит?",
                "answer": "картошка",
                "alternatives": ["игла", "булавка", "шторм"]
            },
            {
                "question": "Что принадлежит тебе, но другие используют это чаще?",
                "answer": "имя",
                "alternatives": ["телефон", "деньги", "машина"]
            },
            {
                "question": "Что может быть разбито одним словом?",
                "answer": "молчание",
                "alternatives": ["стекло", "лёд", "сердце"]
            },
            {
                "question": "Что имеет города, но нет домов; горы, но нет деревьев; воду, но нет рыб?",
                "answer": "карта",
                "alternatives": ["глобус", "атлас", "план"]
            },
            {
                "question": "Что становится мокрым, когда сушит?",
                "answer": "полотенце",
                "alternatives": ["солнце", "ветер", "огонь"]
            },
            {
                "question": "Что можно держать в правой руке, но никогда в левой?",
                "answer": "левую руку",
                "alternatives": ["правую руку", "локоть", "запястье"]
            }
        ]
    
    def generate_riddle(self) -> Tuple[str, str, List[str], int]:
        """Генерирует загадку с вариантами ответов и правильным направлением"""
        riddle_data = random.choice(self.riddles)
        
        # Создаем варианты ответов (правильный + неправильные)
        correct_answer = riddle_data["answer"]
        wrong_answers = riddle_data["alternatives"][:3]  # Берем до 3 неправильных
        
        # Перемешиваем варианты
        all_answers = [correct_answer] + wrong_answers
        random.shuffle(all_answers)
        
        # Определяем позиции (верх-лево, верх-право, низ-лево, низ-право)
        positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right']
        random.shuffle(positions)
        
        # Находим индекс правильного ответа
        correct_index = all_answers.index(correct_answer)
        correct_position = positions[correct_index]
        
        # Определяем направление выхода на основе позиции
        position_to_direction = {
            'top-left': 'up',
            'top-right': 'up', 
            'bottom-left': 'down',
            'bottom-right': 'down'
        }
        correct_direction = position_to_direction[correct_position]
        
        return (riddle_data["question"], correct_answer, all_answers, 
                positions, correct_direction, correct_position)


class Maze:
    """Класс лабиринта"""
    
    def __init__(self, width: int = 21, height: int = 21):
        self.width = width
        self.height = height
        self.grid = []
        self.player_pos = (1, 1)
        self.sphinx_pos = None
        self.exits = {}  # Позиции выходов и их направления
        self.riddle = None
        self.riddle_generator = Riddle()
        
        self.generate_maze()
    
    def generate_maze(self):
        """Генерирует лабиринт используя алгоритм Recursive Backtracker"""
        # Инициализируем сетку стенами
        self.grid = [[CELL_WALL for _ in range(self.width)] for _ in range(self.height)]
        
        # Начинаем с позиции (1, 1)
        start_x, start_y = 1, 1
        self.grid[start_y][start_x] = CELL_PATH
        
        stack = [(start_x, start_y)]
        
        while stack:
            x, y = stack[-1]
            
            # Получаем непосещенных соседей (через 2 клетки)
            neighbors = []
            for dx, dy in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
                nx, ny = x + dx, y + dy
                if (1 <= nx < self.width - 1 and 
                    1 <= ny < self.height - 1 and 
                    self.grid[ny][nx] == CELL_WALL):
                    neighbors.append((nx, ny, dx // 2, dy // 2))
            
            if neighbors:
                # Выбираем случайного соседа
                nx, ny, wx, wy = random.choice(neighbors)
                
                # Удаляем стену между текущей клеткой и соседом
                self.grid[y + wy][x + wx] = CELL_PATH
                self.grid[ny][nx] = CELL_PATH
                
                stack.append((nx, ny))
            else:
                stack.pop()
        
        # Устанавливаем позицию игрока
        self.player_pos = (1, 1)
        
        # Размещаем Сфинкса в случайной доступной позиции (подальше от старта)
        available_positions = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if (self.grid[y][x] == CELL_PATH and 
                    abs(x - 1) + abs(y - 1) > min(self.width, self.height) // 2):
                    available_positions.append((x, y))
        
        if available_positions:
            self.sphinx_pos = random.choice(available_positions)
            self.grid[self.sphinx_pos[1]][self.sphinx_pos[0]] = CELL_SPHINX
        else:
            # Если нет доступных позиций, ставим в центр
            cx, cy = self.width // 2, self.height // 2
            while self.grid[cy][cx] != CELL_PATH:
                cx += 1
                if cx >= self.width - 1:
                    cx = 1
                    cy += 1
            self.sphinx_pos = (cx, cy)
            self.grid[cy][cx] = CELL_SPHINX
        
        # Создаем выходы вокруг Сфинкса
        self.create_exits()
    
    def create_exits(self):
        """Создает 4 выхода вокруг Сфинкса"""
        sx, sy = self.sphinx_pos
        
        # Позиции для выходов (диагонали от Сфинкса)
        exit_positions = [
            (sx - 1, sy - 1, 'top-left'),
            (sx + 1, sy - 1, 'top-right'),
            (sx - 1, sy + 1, 'bottom-left'),
            (sx + 1, sy + 1, 'bottom-right')
        ]
        
        self.exits = {}
        for ex, ey, pos_name in exit_positions:
            if (0 <= ex < self.width and 0 <= ey < self.height and 
                self.grid[ey][ex] == CELL_WALL):
                self.grid[ey][ex] = CELL_EXIT
                self.exits[(ex, ey)] = pos_name
    
    def regenerate_after_riddle(self, correct_exit_pos: Tuple[int, int]):
        """Пересоздает лабиринт после успешного ответа, игрок попадает в новый лабиринт"""
        old_correct_pos_name = self.exits.get(correct_exit_pos, 'unknown')
        
        # Генерируем новый лабиринт
        self.generate_maze()
        
        return old_correct_pos_name
    
    def get_state_key(self, player_pos: Tuple[int, int], has_riddle: bool) -> str:
        """Создает ключ состояния для Q-learning"""
        sx, sy = self.sphinx_pos
        px, py = player_pos
        
        # Простое представление: расстояние до Сфинкса и наличие загадки
        dx = sx - px
        dy = sy - py
        
        riddle_flag = "R" if has_riddle else "N"
        return f"{dx}:{dy}:{riddle_flag}"
    
    def render(self) -> str:
        """Рендерит лабиринт в строку"""
        lines = []
        
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                if (x, y) == self.player_pos:
                    row += CELL_PLAYER
                elif (x, y) == self.sphinx_pos:
                    row += CELL_SPHINX
                elif (x, y) in self.exits:
                    row += CELL_EXIT
                else:
                    row += self.grid[y][x]
            lines.append(row)
        
        return '\n'.join(lines)


class AI:
    """ИИ агент с Q-learning"""
    
    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.95, 
                 exploration_rate: float = 1.0, exploration_decay: float = 0.995):
        self.q_table: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay
        self.actions = list(DIRECTIONS.keys())
        
        self.total_rewards = 0
        self.episodes = 0
        self.wins = 0
        self.losses = 0
    
    def get_action(self, state: str, training: bool = True) -> str:
        """Выбирает действие на основе ε-greedy стратегии"""
        if training and random.random() < self.exploration_rate:
            return random.choice(self.actions)
        
        # Выбираем действие с максимальным Q-значением
        q_values = self.q_table[state]
        if not q_values:
            return random.choice(self.actions)
        
        max_q = max(q_values.values())
        best_actions = [a for a, q in q_values.items() if q == max_q]
        return random.choice(best_actions)
    
    def update(self, state: str, action: str, reward: float, next_state: str, done: bool):
        """Обновляет Q-таблицу"""
        current_q = self.q_table[state][action]
        
        if done:
            max_next_q = 0
        else:
            next_q_values = self.q_table[next_state]
            max_next_q = max(next_q_values.values()) if next_q_values else 0
        
        # Формула Q-learning
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        self.q_table[state][action] = new_q
        
        self.total_rewards += reward
        
        # Уменьшаем исследование со временем
        if self.exploration_rate > 0.01:
            self.exploration_rate *= self.exploration_decay
    
    def save_model(self, filename: str = "ai_model.json"):
        """Сохраняет модель в JSON файл"""
        model_data = {
            "q_table": {k: dict(v) for k, v in self.q_table.items()},
            "exploration_rate": self.exploration_rate,
            "stats": {
                "total_rewards": self.total_rewards,
                "episodes": self.episodes,
                "wins": self.wins,
                "losses": self.losses
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Модель сохранена в {filename}")
    
    def load_model(self, filename: str = "ai_model.json") -> bool:
        """Загружает модель из JSON файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
            
            self.q_table = defaultdict(lambda: defaultdict(float))
            for state, actions in model_data["q_table"].items():
                for action, value in actions.items():
                    self.q_table[state][action] = value
            
            self.exploration_rate = model_data.get("exploration_rate", 1.0)
            
            stats = model_data.get("stats", {})
            self.total_rewards = stats.get("total_rewards", 0)
            self.episodes = stats.get("episodes", 0)
            self.wins = stats.get("wins", 0)
            self.losses = stats.get("losses", 0)
            
            print(f"\n📂 Модель загружена из {filename}")
            print(f"   Исследование: {self.exploration_rate:.3f}")
            print(f"   Эпизодов: {self.episodes}, Побед: {self.wins}, Поражений: {self.losses}")
            return True
        except FileNotFoundError:
            print(f"\n⚠️  Файл модели {filename} не найден. Начинаем с нуля.")
            return False
        except Exception as e:
            print(f"\n❌ Ошибка загрузки модели: {e}")
            return False
    
    def print_stats(self):
        """Выводит статистику обучения"""
        win_rate = (self.wins / self.episodes * 100) if self.episodes > 0 else 0
        avg_reward = (self.total_rewards / self.episodes) if self.episodes > 0 else 0
        
        print("\n📊 Статистика ИИ:")
        print(f"   Эпизодов: {self.episodes}")
        print(f"   Побед: {self.wins} ({win_rate:.1f}%)")
        print(f"   Поражений: {self.losses}")
        print(f"   Средняя награда: {avg_reward:.2f}")
        print(f"   Уровень исследования: {self.exploration_rate:.3f}")
        print(f"   Размер Q-таблицы: {len(self.q_table)} состояний")


class Game:
    """Основной класс игры"""
    
    def __init__(self):
        self.maze = Maze()
        self.ai = AI()
        self.riddle_gen = Riddle()
        self.current_riddle = None
        self.in_riddle_mode = False
        self.correct_exit_pos = None
        self.level = 1
        self.running = True
    
    def clear_screen(self):
        """Очищает экран терминала"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def handle_riddle(self) -> bool:
        """Обрабатывает встречу со Сфинксом"""
        self.clear_screen()
        
        print("🦁 СФИНКС БЛОКИРУЕТ ПУТЬ!")
        print("=" * 50)
        print(self.maze.render())
        print("=" * 50)
        
        # Генерируем загадку
        question, answer, answers, positions, correct_direction, correct_position = \
            self.riddle_gen.generate_riddle()
        
        self.current_riddle = {
            'question': question,
            'answer': answer,
            'answers': answers,
            'positions': positions,
            'correct_direction': correct_direction,
            'correct_position': correct_position
        }
        
        # Находим позицию правильного выхода
        for pos, pos_name in self.maze.exits.items():
            if pos_name == correct_position:
                self.correct_exit_pos = pos
                break
        
        print(f"\n📜 ЗАГАДКА: {question}\n")
        print("Выберите правильный выход:")
        print()
        
        # Отображаем выходы с вариантами ответов
        for i, (ans, pos) in enumerate(zip(answers, positions)):
            symbol = DIRECTION_SYMBOLS.get(
                'up' if 'top' in pos else 'down', 
                '?'
            )
            print(f"  {i+1}. {symbol} [{pos.replace('-', ' ').title()}]: {ans}")
        
        print(f"\n  5. Посмотреть на лабиринт еще раз")
        print()
        
        return True
    
    def get_player_riddle_choice(self) -> Optional[int]:
        """Получает выбор игрока для загадки"""
        while True:
            try:
                choice = input("Ваш выбор (1-5): ").strip()
                if choice == '5':
                    self.clear_screen()
                    print(self.maze.render())
                    input("\nНажмите Enter чтобы продолжить...")
                    self.clear_screen()
                    continue
                
                choice_num = int(choice)
                if 1 <= choice_num <= 4:
                    return choice_num - 1
                else:
                    print("❌ Выберите число от 1 до 5")
            except ValueError:
                print("❌ Введите число")
    
    def train_ai_episode(self, max_steps: int = 500, render: bool = False, 
                         delay: float = 0.05) -> bool:
        """Один эпизод обучения ИИ"""
        self.maze = Maze()
        state = self.maze.get_state_key(self.maze.player_pos, False)
        total_reward = 0
        steps = 0
        won = False
        
        for step in range(max_steps):
            steps = step + 1
            
            # Выбор действия
            action = self.ai.get_action(state, training=True)
            
            # Выполнение действия
            dx, dy = DIRECTIONS[action]
            new_x = self.maze.player_pos[0] + dx
            new_y = self.maze.player_pos[1] + dy
            
            reward = -0.01  # Небольшой штраф за каждый шаг (поощряет быстроту)
            done = False
            
            # Проверка границ и стен
            if (0 <= new_x < self.maze.width and 
                0 <= new_y < self.maze.height and 
                self.maze.grid[new_y][new_x] != CELL_WALL):
                
                self.maze.player_pos = (new_x, new_y)
                
                # Проверка встречи со Сфинксом
                if self.maze.player_pos == self.maze.sphinx_pos:
                    # Генерируем загадку
                    _, _, _, _, correct_direction, correct_position = \
                        self.riddle_gen.generate_riddle()
                    
                    # Находим правильный выход
                    correct_exit = None
                    for pos, pos_name in self.maze.exits.items():
                        if pos_name == correct_position:
                            correct_exit = pos
                            break
                    
                    # ИИ должен выбрать выход
                    # Для простоты: проверяем, знает ли ИИ правильное направление
                    riddle_state = self.maze.get_state_key(self.maze.player_pos, True)
                    
                    # Если ИИ уже обучен, он выберет лучшее действие
                    ai_choice = self.ai.get_action(riddle_state, training=False)
                    
                    # Проверяем, ведет ли выбранное действие к правильному выходу
                    chosen_dx, chosen_dy = DIRECTIONS[ai_choice]
                    chosen_x = new_x + chosen_dx
                    chosen_y = new_y + chosen_dy
                    
                    if (chosen_x, chosen_y) == correct_exit:
                        reward += 10  # Большая награда за правильный ответ
                        won = True
                        done = True
                        self.ai.wins += 1
                    else:
                        reward -= 5  # Штраф за неправильный ответ
                        done = True
                        self.ai.losses += 1
                
                # Проверка выхода из лабиринта (если ИИ случайно вышел)
                elif self.maze.grid[new_y][new_x] == CELL_EXIT:
                    # Выход без загадки - плохо
                    reward -= 2
                    done = True
                    self.ai.losses += 1
            else:
                reward -= 0.5  # Штраф за попытку пойти в стену
            
            # Новый состояние
            next_state = self.maze.get_state_key(self.maze.player_pos, self.maze.player_pos == self.maze.sphinx_pos)
            
            # Обновление Q-таблицы
            self.ai.update(state, action, reward, next_state, done)
            
            state = next_state
            total_reward += reward
            
            if render and step % 10 == 0:
                self.clear_screen()
                print(f"Эпизод обучения | Шаг: {step}/{max_steps}")
                print(f"Позиция: {self.maze.player_pos}, Сфинкс: {self.maze.sphinx_pos}")
                print(self.maze.render())
                print(f"Награда: {reward:.2f}, Исследование: {self.ai.exploration_rate:.3f}")
                time.sleep(delay)
            
            if done:
                break
        
        self.ai.episodes += 1
        return won
    
    def play_human(self):
        """Режим игры для человека"""
        print("\n🎮 РЕЖИМ ИГРЫ ДЛЯ ЧЕЛОВЕКА")
        print("=" * 50)
        print("Управление: W/A/S/D или стрелки + Enter")
        print("Цель: Найти Сфинкса, отгадать загадку и выбрать правильный выход")
        print("=" * 50)
        input("Нажмите Enter чтобы начать...")
        
        while self.running:
            self.clear_screen()
            
            print(f"🏰 Уровень: {self.level}")
            print("=" * 50)
            print(self.maze.render())
            print("=" * 50)
            print(f"Позиция: {self.maze.player_pos}")
            print(f"Сфинкс: {self.maze.sphinx_pos}")
            print()
            print("W - Вверх, A - Влево, S - Вниз, D - Вправо, Q - Выход")
            print()
            
            # Проверка встречи со Сфинксом
            if self.maze.player_pos == self.maze.sphinx_pos:
                if self.handle_riddle():
                    choice = self.get_player_riddle_choice()
                    
                    if choice is not None and 0 <= choice <= 3:
                        chosen_position = self.current_riddle['positions'][choice]
                        
                        # Находим координаты правильного выхода
                        correct_pos_name = self.current_riddle['correct_position']
                        
                        if chosen_position == correct_pos_name:
                            print("\n✅ ПРАВИЛЬНО! Сфинкс пропускает вас.")
                            time.sleep(1)
                            
                            # Регенерируем лабиринт
                            old_pos_name = self.maze.regenerate_after_riddle(self.correct_exit_pos)
                            self.level += 1
                            print(f"\n🎉 Новый уровень! Вы прошли через выход: {old_pos_name}")
                            time.sleep(1)
                        else:
                            print(f"\n❌ НЕПРАВИЛЬНО! Правильный ответ был: {self.current_riddle['answer']}")
                            print(f"Правильный выход: {correct_pos_name}")
                            time.sleep(2)
                            print("\n💀 Игра окончена. Попробуйте снова!")
                            time.sleep(2)
                            self.maze = Maze()
                            self.level = 1
            
            # Обработка ввода
            try:
                move = input("Ход: ").strip().lower()
                
                if move == 'q':
                    print("\nДо свидания!")
                    self.running = False
                    break
                
                dx, dy = 0, 0
                if move in ['w', 'ц']:
                    dy = -1
                elif move in ['s', 'ы']:
                    dy = 1
                elif move in ['a', 'ф']:
                    dx = -1
                elif move in ['d', 'в']:
                    dx = 1
                elif move in ['up', 'вверх']:
                    dy = -1
                elif move in ['down', 'вниз']:
                    dy = 1
                elif move in ['left', 'влево']:
                    dx = -1
                elif move in ['right', 'вправо']:
                    dx = 1
                else:
                    continue
                
                new_x = self.maze.player_pos[0] + dx
                new_y = self.maze.player_pos[1] + dy
                
                if (0 <= new_x < self.maze.width and 
                    0 <= new_y < self.maze.height and 
                    self.maze.grid[new_y][new_x] != CELL_WALL):
                    self.maze.player_pos = (new_x, new_y)
                
            except KeyboardInterrupt:
                print("\n\nИгра прервана. До свидания!")
                self.running = False
                break
    
    def train_ai(self, episodes: int = 1000, render_interval: int = 100):
        """Режим обучения ИИ"""
        print("\n🤖 РЕЖИМ ОБУЧЕНИЯ ИИ")
        print("=" * 50)
        print(f"Эпизодов для обучения: {episodes}")
        print(f"Показывать каждые {render_interval} эпизодов")
        print("=" * 50)
        
        # Попытка загрузить существующую модель
        self.ai.load_model()
        
        input("Нажмите Enter чтобы начать обучение...")
        
        start_time = time.time()
        
        for episode in range(1, episodes + 1):
            won = self.train_ai_episode(max_steps=300)
            
            if episode % render_interval == 0 or episode == episodes:
                elapsed = time.time() - start_time
                eps_per_sec = episode / elapsed if elapsed > 0 else 0
                
                self.clear_screen()
                print(f"📊 Обучение: Эпизод {episode}/{episodes}")
                print(f"Время: {elapsed:.1f}с ({eps_per_sec:.1f} эп/с)")
                print("=" * 50)
                self.ai.print_stats()
                print()
                print("Пример лабиринта:")
                print(self.maze.render())
                print()
                
                if episode < episodes:
                    cont = input("Продолжить обучение? (Y/n): ").strip().lower()
                    if cont == 'n':
                        break
        
        # Сохраняем модель
        self.ai.save_model()
        self.ai.print_stats()
    
    def watch_ai(self, episodes: int = 10, delay: float = 0.2):
        """Режим наблюдения за обученным ИИ"""
        print("\n👁️ НАБЛЮДЕНИЕ ЗА ИИ")
        print("=" * 50)
        
        # Загружаем модель
        if not self.ai.load_model():
            print("Сначала обучите ИИ!")
            return
        
        # Отключаем исследование для демонстрации
        old_exploration = self.ai.exploration_rate
        self.ai.exploration_rate = 0.05
        
        for episode in range(1, episodes + 1):
            self.maze = Maze()
            state = self.maze.get_state_key(self.maze.player_pos, False)
            steps = 0
            won = False
            
            self.clear_screen()
            print(f"🎬 Эпизод {episode}/{episodes}")
            print("=" * 50)
            
            for step in range(300):
                steps = step + 1
                
                action = self.ai.get_action(state, training=False)
                
                dx, dy = DIRECTIONS[action]
                new_x = self.maze.player_pos[0] + dx
                new_y = self.maze.player_pos[1] + dy
                
                if (0 <= new_x < self.maze.width and 
                    0 <= new_y < self.maze.height and 
                    self.maze.grid[new_y][new_x] != CELL_WALL):
                    self.maze.player_pos = (new_x, new_y)
                
                print(self.maze.render())
                print(f"\nШаг: {steps} | Действие: {DIRECTION_SYMBOLS.get(action, '?')} {action}")
                print(f"Позиция: {self.maze.player_pos} | Сфинкс: {self.maze.sphinx_pos}")
                
                if self.maze.player_pos == self.maze.sphinx_pos:
                    print("\n🦁 Сфинкс задает загадку!")
                    time.sleep(1)
                    
                    # ИИ решает загадку
                    _, _, _, _, correct_direction, correct_position = \
                        self.riddle_gen.generate_riddle()
                    
                    # Находим правильный выход
                    correct_exit = None
                    for pos, pos_name in self.maze.exits.items():
                        if pos_name == correct_position:
                            correct_exit = pos
                            break
                    
                    riddle_state = self.maze.get_state_key(self.maze.player_pos, True)
                    ai_choice = self.ai.get_action(riddle_state, training=False)
                    
                    chosen_dx, chosen_dy = DIRECTIONS[ai_choice]
                    chosen_x = new_x + chosen_dx
                    chosen_y = new_y + chosen_dy
                    
                    print(f"ИИ выбирает: {DIRECTION_SYMBOLS.get(ai_choice, '?')} {ai_choice}")
                    time.sleep(1)
                    
                    if (chosen_x, chosen_y) == correct_exit:
                        print("\n✅ ИИ отгадал загадку!")
                        won = True
                        time.sleep(1)
                        break
                    else:
                        print(f"\n❌ ИИ ошибся! Правильный выход: {correct_position}")
                        time.sleep(1)
                        break
                
                time.sleep(delay)
                state = self.maze.get_state_key(self.maze.player_pos, False)
            
            if won:
                print(f"\n🎉 Эпизод {episode}: ПОБЕДА за {steps} шагов!")
            else:
                print(f"\n💀 Эпизод {episode}: ПРОИГРЫШ на шаге {steps}")
            
            if episode < episodes:
                time.sleep(1)
        
        # Восстанавливаем исследование
        self.ai.exploration_rate = old_exploration
    
    def main_menu(self):
        """Главное меню"""
        while True:
            self.clear_screen()
            print("🏰 ЛАБИРИНТ СО СФИНКСОМ 🦁")
            print("=" * 50)
            print("1. 🎮 Играть за человека")
            print("2. 🤖 Обучить ИИ")
            print("3. 👁️ Наблюдать за ИИ")
            print("4. 📊 Статистика ИИ")
            print("5. 💾 Сохранить модель")
            print("6. 📂 Загрузить модель")
            print("7. ❌ Выход")
            print("=" * 50)
            
            choice = input("Выберите опцию (1-7): ").strip()
            
            if choice == '1':
                self.play_human()
            elif choice == '2':
                try:
                    episodes = int(input("Количество эпизодов (по умолчанию 1000): ").strip() or "1000")
                    render_int = int(input("Показывать каждые ... эпизодов (по умолчанию 100): ").strip() or "100")
                    self.train_ai(episodes, render_int)
                except ValueError:
                    print("❌ Неверное число")
                    time.sleep(1)
            elif choice == '3':
                try:
                    episodes = int(input("Количество эпизодов для наблюдения (по умолчанию 10): ").strip() or "10")
                    delay = float(input("Задержка между шагами в секундах (по умолчанию 0.2): ").strip() or "0.2")
                    self.watch_ai(episodes, delay)
                except ValueError:
                    print("❌ Неверное число")
                    time.sleep(1)
            elif choice == '4':
                self.ai.print_stats()
                input("\nНажмите Enter чтобы продолжить...")
            elif choice == '5':
                filename = input("Имя файла (по умолчанию ai_model.json): ").strip() or "ai_model.json"
                self.ai.save_model(filename)
                input("\nНажмите Enter чтобы продолжить...")
            elif choice == '6':
                filename = input("Имя файла (по умолчанию ai_model.json): ").strip() or "ai_model.json"
                self.ai.load_model(filename)
                input("\nНажмите Enter чтобы продолжить...")
            elif choice == '7':
                print("\nДо свидания! 🦁")
                break
            else:
                print("❌ Неверный выбор")
                time.sleep(1)


if __name__ == "__main__":
    game = Game()
    try:
        game.main_menu()
    except KeyboardInterrupt:
        print("\n\nИгра прервана. До свидания!")
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
