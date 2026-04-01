#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Терминальная игра с загадками и обучающимся ИИ
ИИ использует обучение с подкреплением (Q-learning)
"""

import random
import json
import os
from collections import defaultdict
from datetime import datetime

class RiddleGame:
    """Класс игры с загадками"""
    
    def __init__(self):
        self.riddles = [
            {
                "question": "Зимой и летом одним цветом?",
                "answers": ["ёлка", "елка", "сосна", "дерево"],
                "correct": 0
            },
            {
                "question": "Что можно разбить, даже не дотрагиваясь до него?",
                "answers": ["обещание", "сердце", "мечта", "тишина"],
                "correct": 0
            },
            {
                "question": "Чем больше из неё берёшь, тем больше она становится?",
                "answers": ["яма", "дыра", "пропасть", "колодец"],
                "correct": 0
            },
            {
                "question": "Что принадлежит тебе, но другие используют это чаще?",
                "answers": ["имя", "телефон", "деньги", "время"],
                "correct": 0
            },
            {
                "question": "Какой рукой лучше всего размешивать чай?",
                "answers": ["правой", "левой", "ложкой", "обеими"],
                "correct": 2
            },
            {
                "question": "Что имеет города, но не домов; горы, но не деревьев; воду, но не рыб?",
                "answers": ["карта", "глобус", "мечта", "картина"],
                "correct": 0
            },
            {
                "question": "Можно ли прыгнуть выше дома?",
                "answers": ["да", "нет", "только летом", "зависит от дома"],
                "correct": 0
            },
            {
                "question": "Что становится больше, если поставить вверх ногами?",
                "answers": ["число 6", "стул", "человек", "дерево"],
                "correct": 0
            },
            {
                "question": "У бабушки три кошки: Мурка, Клава и Лиза. Они спят на трёх разных подушках: жёлтой, розовой и синей. Клава спит на розовой или синей подушке. Мурка не спит на розовой. На какой подушке спит каждая кошка?",
                "answers": ["Клава-синяя, Мурка-жёлтая, Лиза-розовая", "Клава-розовая, Мурка-синяя, Лиза-жёлтая", "Клава-синяя, Мурка-розовая, Лиза-жёлтая", "невозможно определить"],
                "correct": 0
            },
            {
                "question": "Что не имеет длины, глубины, ширины, высоты, а можно измерить?",
                "answers": ["время", "температура", "скорость", "расстояние"],
                "correct": 0
            }
        ]
        
        self.current_riddle_index = None
        self.score = 0
        self.total_questions = 0
        
    def get_random_riddle(self):
        """Получить случайную загадку"""
        self.current_riddle_index = random.randint(0, len(self.riddles) - 1)
        return self.riddles[self.current_riddle_index]
    
    def check_answer(self, answer_index):
        """Проверить ответ"""
        if self.current_riddle_index is None:
            return False
            
        riddle = self.riddles[self.current_riddle_index]
        is_correct = answer_index == riddle["correct"]
        
        self.total_questions += 1
        if is_correct:
            self.score += 1
            
        return is_correct
    
    def get_state(self, riddle_index=None):
        """Получить состояние для ИИ"""
        if riddle_index is None:
            riddle_index = self.current_riddle_index
        return f"riddle_{riddle_index}"
    
    def reset(self):
        """Сбросить игру"""
        self.score = 0
        self.total_questions = 0
        self.current_riddle_index = None


class QLearningAI:
    """ИИ с обучением с подкреплением (Q-learning)"""
    
    def __init__(self, learning_rate=0.1, discount_factor=0.95, exploration_rate=1.0):
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.learning_rate = learning_rate  # Скорость обучения
        self.discount_factor = discount_factor  # Фактор дисконтирования
        self.exploration_rate = exploration_rate  # Вероятность исследования
        self.min_exploration_rate = 0.01  # Минимальная вероятность исследования
        self.exploration_decay = 0.995  # Затухание исследования
        
    def get_action(self, state, n_actions):
        """Выбрать действие (ответ)"""
        # Исследование или использование
        if random.random() < self.exploration_rate:
            return random.randint(0, n_actions - 1)
        else:
            # Выбор лучшего известного действия
            q_values = self.q_table[state]
            if not q_values:
                return random.randint(0, n_actions - 1)
            
            max_q = max(q_values.values()) if q_values else 0
            best_actions = [a for a, q in q_values.items() if q == max_q]
            
            if best_actions:
                return random.choice(best_actions)
            else:
                return random.randint(0, n_actions - 1)
    
    def update(self, state, action, reward, next_state, n_actions):
        """Обновить Q-таблицу"""
        current_q = self.q_table[state][action]
        
        # Найти максимальное Q-значение для следующего состояния
        if self.q_table[next_state]:
            max_next_q = max(self.q_table[next_state].values())
        else:
            max_next_q = 0
        
        # Формула Q-learning
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[state][action] = new_q
        
        # Уменьшить вероятность исследования
        if self.exploration_rate > self.min_exploration_rate:
            self.exploration_rate *= self.exploration_decay
    
    def save_model(self, filename="ai_model.json"):
        """Сохранить модель ИИ"""
        model_data = {
            "q_table": dict(self.q_table),
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
            "exploration_rate": self.exploration_rate,
            "training_stats": {
                "timestamp": datetime.now().isoformat()
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Модель сохранена в {filename}")
    
    def load_model(self, filename="ai_model.json"):
        """Загрузить модель ИИ"""
        if not os.path.exists(filename):
            print(f"\n⚠️  Файл модели {filename} не найден. Начинаем с нуля.")
            return False
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
            
            self.q_table = defaultdict(lambda: defaultdict(float))
            for state, actions in model_data["q_table"].items():
                for action, value in actions.items():
                    self.q_table[state][int(action)] = float(value)
            
            self.exploration_rate = model_data.get("exploration_rate", 1.0)
            
            print(f"\n✅ Модель загружена из {filename}")
            print(f"   Уровень исследования: {self.exploration_rate:.3f}")
            return True
        except Exception as e:
            print(f"\n❌ Ошибка загрузки модели: {e}")
            return False
    
    def get_statistics(self):
        """Получить статистику обучения"""
        total_states = len(self.q_table)
        total_entries = sum(len(actions) for actions in self.q_table.values())
        
        return {
            "states_learned": total_states,
            "total_q_entries": total_entries,
            "exploration_rate": self.exploration_rate
        }


class GameInterface:
    """Интерфейс для взаимодействия с игрой"""
    
    def __init__(self):
        self.game = RiddleGame()
        self.ai = QLearningAI()
        self.mode = "human"  # "human" или "ai"
        self.training_mode = False
        
    def clear_screen(self):
        """Очистить экран"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_menu(self):
        """Показать главное меню"""
        print("\n" + "="*60)
        print("🧩 ТЕРМИНАЛЬНАЯ ИГРА С ЗАГАДКАМИ И ИИ 🧩")
        print("="*60)
        print("\n1. 🎮 Играть человеку")
        print("2. 🤖 Обучать ИИ (автоматический режим)")
        print("3. 👁️  Наблюдать за игрой ИИ")
        print("4. 📊 Показать статистику ИИ")
        print("5. 💾 Сохранить модель ИИ")
        print("6. 📂 Загрузить модель ИИ")
        print("7. ❌ Выход")
        print("="*60)
    
    def play_human(self):
        """Режим игры для человека"""
        self.clear_screen()
        print("\n🎮 РЕЖИМ ИГРЫ ДЛЯ ЧЕЛОВЕКА")
        print("="*60)
        
        while True:
            riddle = self.game.get_random_riddle()
            
            print(f"\n❓ Загадка: {riddle['question']}")
            print("\nВарианты ответов:")
            
            for i, answer in enumerate(riddle['answers']):
                print(f"  {i+1}. {answer}")
            
            print("\n0. Выход в меню")
            
            try:
                choice = input("\nВаш ответ (цифра): ").strip()
                
                if choice == '0':
                    break
                
                choice_idx = int(choice) - 1
                
                if 0 <= choice_idx < len(riddle['answers']):
                    is_correct = self.game.check_answer(choice_idx)
                    
                    if is_correct:
                        print("\n✅ Правильно! Молодец!")
                    else:
                        correct_answer = riddle['answers'][riddle['correct']]
                        print(f"\n❌ Неверно. Правильный ответ: {correct_answer}")
                    
                    print(f"📊 Счёт: {self.game.score}/{self.game.total_questions}")
                else:
                    print("\n⚠️  Неверный номер ответа!")
                    
            except ValueError:
                print("\n⚠️  Введите число!")
            except KeyboardInterrupt:
                break
        
        print(f"\n🏁 Игра окончена! Ваш счёт: {self.game.score}/{self.game.total_questions}")
        input("\nНажмите Enter для возврата в меню...")
    
    def train_ai(self, episodes=100, show_progress=True):
        """Обучение ИИ"""
        self.clear_screen()
        print("\n🤖 ОБУЧЕНИЕ ИИ")
        print("="*60)
        
        total_rewards = 0
        correct_answers = 0
        
        for episode in range(episodes):
            riddle = self.game.get_random_riddle()
            state = self.game.get_state()
            n_actions = len(riddle['answers'])
            
            # ИИ выбирает действие
            action = self.ai.get_action(state, n_actions)
            
            # Проверяем ответ
            is_correct = self.game.check_answer(action)
            
            # Награда
            reward = 1 if is_correct else -1
            total_rewards += reward
            
            if is_correct:
                correct_answers += 1
            
            # Следующее состояние (новая загадка)
            next_riddle = self.game.get_random_riddle()
            next_state = self.game.get_state()
            
            # Обновляем Q-таблицу
            self.ai.update(state, action, reward, next_state, n_actions)
            
            # Показываем прогресс
            if show_progress and (episode + 1) % 10 == 0:
                accuracy = correct_answers / (episode + 1) * 100
                print(f"Эпизод {episode+1}/{episodes} | "
                      f"Точность: {accuracy:.1f}% | "
                      f"Исследование: {self.ai.exploration_rate:.3f}")
        
        accuracy = correct_answers / episodes * 100
        print(f"\n✅ Обучение завершено!")
        print(f"📊 Итоговая точность: {accuracy:.1f}%")
        print(f"📈 Всего наград: {total_rewards}")
        
        stats = self.ai.get_statistics()
        print(f"🧠 Изучено состояний: {stats['states_learned']}")
        print(f"🔢 Записей в Q-таблице: {stats['total_q_entries']}")
        
        input("\nНажмите Enter для возврата в меню...")
    
    def observe_ai(self, episodes=10):
        """Наблюдение за игрой ИИ"""
        self.clear_screen()
        print("\n👁️  НАБЛЮДЕНИЕ ЗА ИГРОЙ ИИ")
        print("="*60)
        
        correct = 0
        
        for i in range(episodes):
            riddle = self.game.get_random_riddle()
            state = self.game.get_state()
            n_actions = len(riddle['answers'])
            
            # ИИ выбирает действие (без исследования)
            old_exploration = self.ai.exploration_rate
            self.ai.exploration_rate = 0  # Только использование
            action = self.ai.get_action(state, n_actions)
            self.ai.exploration_rate = old_exploration
            
            is_correct = self.game.check_answer(action)
            
            if is_correct:
                correct += 1
            
            print(f"\n{'='*50}")
            print(f"Загадка {i+1}: {riddle['question']}")
            print(f"Ответ ИИ: {riddle['answers'][action]}")
            
            if is_correct:
                print("✅ Правильно!")
            else:
                print(f"❌ Неверно. Правильный ответ: {riddle['answers'][riddle['correct']]}")
        
        accuracy = correct / episodes * 100
        print(f"\n{'='*50}")
        print(f"📊 Результат: {correct}/{episodes} ({accuracy:.1f}%)")
        
        input("\nНажмите Enter для возврата в меню...")
    
    def show_ai_stats(self):
        """Показать статистику ИИ"""
        self.clear_screen()
        print("\n📊 СТАТИСТИКА ИИ")
        print("="*60)
        
        stats = self.ai.get_statistics()
        
        print(f"\n🧠 Изучено состояний: {stats['states_learned']}")
        print(f"🔢 Записей в Q-таблице: {stats['total_q_entries']}")
        print(f"🎲 Уровень исследования: {stats['exploration_rate']:.3f}")
        
        # Показать топ состояний
        if stats['states_learned'] > 0:
            print("\n📋 Примеры изученных состояний:")
            count = 0
            for state, actions in list(self.ai.q_table.items())[:5]:
                if actions:
                    best_action = max(actions.items(), key=lambda x: x[1])
                    print(f"  {state}: лучший ответ #{best_action[0]} (Q={best_action[1]:.2f})")
                    count += 1
        
        input("\nНажмите Enter для возврата в меню...")
    
    def run(self):
        """Запуск игры"""
        print("\n🎮 Добро пожаловать в игру с загадками и ИИ!")
        
        # Попытка загрузить существующую модель
        if os.path.exists("ai_model.json"):
            choice = input("\n📂 Найдена сохранённая модель. Загрузить? (y/n): ").strip().lower()
            if choice == 'y':
                self.ai.load_model()
        
        while True:
            self.show_menu()
            
            try:
                choice = input("\nВыберите пункт меню (1-7): ").strip()
                
                if choice == '1':
                    self.play_human()
                elif choice == '2':
                    try:
                        episodes = int(input("\nКоличество эпизодов для обучения (по умолчанию 100): ").strip() or "100")
                        self.train_ai(episodes=episodes)
                    except ValueError:
                        print("\n⚠️  Введите число!")
                elif choice == '3':
                    try:
                        episodes = int(input("\nКоличество игр для наблюдения (по умолчанию 10): ").strip() or "10")
                        self.observe_ai(episodes=episodes)
                    except ValueError:
                        print("\n⚠️  Введите число!")
                elif choice == '4':
                    self.show_ai_stats()
                elif choice == '5':
                    self.ai.save_model()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '6':
                    self.ai.load_model()
                    input("\nНажмите Enter для продолжения...")
                elif choice == '7':
                    print("\n👋 До свидания!")
                    break
                else:
                    print("\n⚠️  Неверный выбор!")
                    
            except KeyboardInterrupt:
                print("\n\n👋 До свидания!")
                break
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")


if __name__ == "__main__":
    interface = GameInterface()
    interface.run()
