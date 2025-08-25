#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматического создания ссылок в хранилище Obsidian.
Добавляет wikilinks ([[название]]) при первом упоминании названий файлов в тексте.

Автор: AI Assistant
Версия: 1.0
"""

import os
import re
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime


class ObsidianLinkCreator:
    def __init__(self, vault_path: str, dry_run: bool = True, backup: bool = True):
        """
        Инициализация создателя ссылок Obsidian.
        
        Args:
            vault_path: Путь к хранилищу Obsidian
            dry_run: Если True, только показывает изменения без их применения
            backup: Если True, создает резервную копию перед изменениями
        """
        self.vault_path = Path(vault_path)
        self.dry_run = dry_run
        self.backup = backup
        self.notes: Dict[str, Path] = {}
        self.changes_made = 0
        
        # Паттерны для исключения из обработки
        self.exclude_patterns = [
            r'```[\s\S]*?```',  # Блоки кода
            r'`[^`]+`',         # Инлайн код
            r'\[\[[^\]]+\]\]',  # Существующие wikilinks
            r'!\[\[[^\]]+\]\]', # Встроенные файлы
            r'https?://[^\s]+', # URL
            r'www\.[^\s]+',     # www ссылки
        ]
        
        # Минимальная длина названия для создания ссылки
        self.min_title_length = 3
        
        # Общие окончания для склонений русских слов
        self.russian_endings = [
            'а', 'ам', 'ами', 'ах', 'е', 'ей', 'ем', 'и', 'ов', 'ом', 'у', 'ы', 'я', 'ях',
            'ах', 'ев', 'ём', 'ёй', 'ёх', 'ию', 'ии', 'ией', 'иях', 'ой', 'ою', 'ую', 'юю'
        ]
        
    def scan_vault(self) -> None:
        """Сканирует хранилище и собирает информацию о всех заметках."""
        print(f"Сканирование хранилища: {self.vault_path}")
        
        for root, dirs, files in os.walk(self.vault_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = Path(root) / file
                    # Используем имя файла без расширения как ключ
                    note_name = file_path.stem
                    self.notes[note_name] = file_path
                    
        print(f"Найдено {len(self.notes)} заметок")
        
    def create_backup(self) -> None:
        """Создает резервную копию хранилища."""
        if not self.backup:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.vault_path.parent / f"backup_{self.vault_path.name}_{timestamp}"
        
        print(f"Создание резервной копии: {backup_path}")
        shutil.copytree(self.vault_path, backup_path)
        print("Резервная копия создана")
        
    def is_text_protected(self, text: str, start: int, end: int) -> bool:
        """
        Проверяет, находится ли текст в защищенной области (код, ссылки и т.д.).
        
        Args:
            text: Полный текст
            start: Начальная позиция проверяемого фрагмента
            end: Конечная позиция проверяемого фрагмента
            
        Returns:
            True, если текст находится в защищенной области
        """
        for pattern in self.exclude_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE | re.DOTALL):
                if match.start() <= start < match.end() or match.start() < end <= match.end():
                    return True
        return False
        
    def generate_word_variants(self, word: str) -> List[str]:
        """
        Генерирует возможные варианты склонений для русского слова.
        
        Args:
            word: Исходное слово
            
        Returns:
            Список возможных вариантов слова
        """
        variants = [word]  # Начинаем с исходного слова
        
        # Если слово очень короткое, не пытаемся найти склонения
        if len(word) < 3:
            return variants
            
        # Специальные случаи для составных слов
        if ' ' in word:
            # Для составных названий (например, "Красная Шапка")
            words = word.split()
            if len(words) == 2:
                # Добавляем специфичные склонения для известных составных названий
                variants.extend(self.generate_compound_variants(words[0], words[1]))
                
                # Также склоняем каждое слово отдельно
                first_variants = self.generate_single_word_variants(words[0])
                second_variants = self.generate_single_word_variants(words[1])
                
                # Комбинируем варианты (ограниченно, чтобы не создавать слишком много вариантов)
                for first in first_variants[:5]:  # Берем только первые 5 вариантов
                    for second in second_variants[:5]:
                        combined = f"{first} {second}"
                        if combined not in variants:
                            variants.append(combined)
        else:
            # Для одиночных слов
            variants.extend(self.generate_single_word_variants(word))
                    
        return variants
        
    def generate_compound_variants(self, first_word: str, second_word: str) -> List[str]:
        """
        Генерирует склонения для составных названий с учетом русской грамматики.
        
        Args:
            first_word: Первое слово (обычно прилагательное)
            second_word: Второе слово (обычно существительное)
            
        Returns:
            Список возможных склонений составного названия
        """
        variants = []
        
        # Специальные правила для прилагательных + существительных
        
        # "Красная Шапка" -> "Красных Шапках", "Красной Шапке" и т.д.
        if first_word == "Красная" and second_word == "Шапка":
            variants.extend([
                "Красной Шапки", "Красной Шапке", "Красную Шапку", "Красной Шапкой",
                "Красных Шапок", "Красным Шапкам", "Красные Шапки", "Красными Шапками", "Красных Шапках"
            ])
            
        # "Аркадские Ши" -> "Аркадских Ши", "Аркадским Ши" и т.д.
        elif first_word == "Аркадские" and second_word == "Ши":
            variants.extend([
                "Аркадских Ши", "Аркадским Ши", "Аркадскими Ши", "Аркадское Ши", "Аркадского Ши"
            ])
            
        # "Осенние Ши" -> "Осенних Ши", "Осенним Ши" и т.д.
        elif first_word == "Осенние" and second_word == "Ши":
            variants.extend([
                "Осенних Ши", "Осенним Ши", "Осенними Ши", "Осеннее Ши", "Осеннего Ши"
            ])
            
        # Общие правила для прилагательных
        else:
            # Если первое слово похоже на прилагательное
            if first_word.endswith(('ая', 'ые', 'ие', 'ий', 'ой')):
                # Генерируем основные формы прилагательных
                if first_word.endswith('ая'):  # женский род
                    base = first_word[:-2]
                    adj_variants = [base + 'ой', base + 'ую', base + 'ых', base + 'ым', base + 'ыми']
                elif first_word.endswith('ые'):  # множественное число
                    base = first_word[:-2]
                    adj_variants = [base + 'ых', base + 'ым', base + 'ыми']
                elif first_word.endswith('ие'):  # множественное число
                    base = first_word[:-2]
                    adj_variants = [base + 'их', base + 'им', base + 'ими']
                else:
                    adj_variants = [first_word]
                    
                # Комбинируем с существительным
                for adj in adj_variants:
                    variants.append(f"{adj} {second_word}")
                    
        return variants
        
    def generate_single_word_variants(self, word: str) -> List[str]:
        """
        Генерирует варианты склонений для одного слова.
        
        Args:
            word: Исходное слово
            
        Returns:
            Список возможных вариантов слова
        """
        variants = []
        
        if len(word) < 2:
            return variants
            
        # Специальные правила для разных типов слов
        
        # Слова на -ь (например, "Тролль")
        if word.endswith('ь'):
            base = word[:-1]
            variants.extend([
                base + 'я',     # Тролля
                base + 'ю',     # Троллю  
                base + 'ем',    # Троллем
                base + 'е',     # Тролле
                base + 'и',     # Тролли
                base + 'ей',    # Троллей
                base + 'ям',    # Троллям
                base + 'ями',   # Троллями
                base + 'ях',    # Троллях
            ])
            
        # Слова на -а (например, "Шапка")
        elif word.endswith('а'):
            base = word[:-1]
            variants.extend([
                base + 'ы',     # Шапки
                base + 'е',     # Шапке
                base + 'у',     # Шапку
                base + 'ой',    # Шапкой
                base + 'ах',    # Шапках
                base + 'ам',    # Шапкам
                base + 'ами',   # Шапками
            ])
            
        # Слова на -ы (например, "Дворы")
        elif word.endswith('ы'):
            base = word[:-1]
            variants.extend([
                base + 'ов',    # Дворов
                base + 'ам',    # Дворам
                base + 'ами',   # Дворами
                base + 'ах',    # Дворах
                base,           # Двор (единственное число)
                base + 'а',     # Двора
                base + 'у',     # Двору
                base + 'ом',    # Двором
                base + 'е',     # Дворе
            ])
            
        # Слова на -и (например, "Ши")
        elif word.endswith('и'):
            base = word[:-1]
            variants.extend([
                base + 'ей',    # Шей
                base + 'ям',    # Шям
                base + 'ями',   # Шями
                base + 'ях',    # Шях
                base,           # Ш (маловероятно, но возможно)
            ])
            
        # Мужские слова на согласную (например, "Пак")
        elif word[-1] in 'бвгджзклмнпрстфхцчшщ':
            variants.extend([
                word + 'а',     # Пака
                word + 'у',     # Паку
                word + 'ом',    # Паком
                word + 'е',     # Паке
                word + 'и',     # Паки
                word + 'ов',    # Паков
                word + 'ам',    # Пакам
                word + 'ами',   # Паками
                word + 'ах',    # Паках
            ])
            
        # Общие окончания для всех типов слов
        for ending in self.russian_endings:
            # Вариант с добавлением окончания
            if not word.endswith(ending):
                variants.append(word + ending)
                
            # Вариант с удалением окончания (если слово заканчивается на это окончание)
            if word.endswith(ending) and len(word) > len(ending) + 2:
                base = word[:-len(ending)]
                if base not in variants:
                    variants.append(base)
                    
        return list(set(variants))  # Убираем дубликаты
        
    def find_potential_links(self, content: str, current_note: str) -> List[Tuple[str, int, int, str]]:
        """
        Находит потенциальные места для создания ссылок.
        
        Args:
            content: Содержимое заметки
            current_note: Имя текущей заметки (чтобы не ссылаться на себя)
            
        Returns:
            Список кортежей (название_заметки, начало, конец, исходный_текст)
        """
        potential_links = []
        
        # Сортируем заметки по длине названия (от длинных к коротким)
        # чтобы сначала обрабатывать более специфичные названия
        sorted_notes = sorted(
            [name for name in self.notes.keys() if name != current_note and len(name) >= self.min_title_length],
            key=len,
            reverse=True
        )
        
        for note_name in sorted_notes:
            # Генерируем варианты склонений для поиска
            word_variants = self.generate_word_variants(note_name)
            
            for variant in word_variants:
                # Ищем точные совпадения слов (с границами слов), игнорируя регистр
                pattern = r'\b' + re.escape(variant) + r'\b'
                
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    start, end = match.span()
                    original_text = content[start:end]  # Сохраняем исходное написание
                    
                    # Проверяем, что текст не в защищенной области
                    if not self.is_text_protected(content, start, end):
                        potential_links.append((note_name, start, end, original_text))
                    
        return potential_links
        
    def apply_links_to_content(self, content: str, current_note: str) -> Tuple[str, int]:
        """
        Применяет ссылки к содержимому заметки.
        
        Args:
            content: Исходное содержимое
            current_note: Имя текущей заметки
            
        Returns:
            Кортеж (новое_содержимое, количество_добавленных_ссылок)
        """
        potential_links = self.find_potential_links(content, current_note)
        
        if not potential_links:
            return content, 0
            
        # Группируем ссылки по названиям и оставляем только первое вхождение каждой
        seen_notes: Set[str] = set()
        unique_links = []
        
        # Сортируем по позиции в тексте
        potential_links.sort(key=lambda x: x[1])
        
        for note_name, start, end, original_text in potential_links:
            if note_name.lower() not in seen_notes:
                unique_links.append((note_name, start, end, original_text))
                seen_notes.add(note_name.lower())
                
        if not unique_links:
            return content, 0
            
        # Применяем изменения от конца к началу, чтобы не сбить позиции
        new_content = content
        links_added = 0
        
        for note_name, start, end, original_text in reversed(unique_links):
            # Проверяем, что позиции все еще валидны после предыдущих изменений
            if start < len(new_content) and end <= len(new_content):
                # Создаем ссылку с сохранением исходного написания
                if original_text == note_name:
                    # Если исходный текст точно совпадает с названием файла
                    link_text = f"[[{note_name}]]"
                else:
                    # Если есть различия в регистре или склонении, используем alias
                    link_text = f"[[{note_name}|{original_text}]]"
                
                new_content = new_content[:start] + link_text + new_content[end:]
                links_added += 1
                
        return new_content, links_added
        
    def process_note(self, note_path: Path) -> bool:
        """
        Обрабатывает одну заметку.
        
        Args:
            note_path: Путь к заметке
            
        Returns:
            True, если были внесены изменения
        """
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                
            note_name = note_path.stem
            new_content, links_added = self.apply_links_to_content(original_content, note_name)
            
            if links_added > 0:
                if self.dry_run:
                    print(f"[ПРОБНЫЙ ЗАПУСК] {note_path.relative_to(self.vault_path)}: добавлено бы {links_added} ссылок")
                else:
                    with open(note_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"✓ {note_path.relative_to(self.vault_path)}: добавлено {links_added} ссылок")
                    
                self.changes_made += links_added
                return True
                
        except Exception as e:
            print(f"✗ Ошибка при обработке {note_path}: {e}")
            
        return False
        
    def process_all_notes(self) -> None:
        """Обрабатывает все заметки в хранилище."""
        print(f"\nОбработка заметок (режим: {'пробный запуск' if self.dry_run else 'применение изменений'})...")
        
        processed = 0
        modified = 0
        
        for note_name, note_path in self.notes.items():
            if self.process_note(note_path):
                modified += 1
            processed += 1
            
        print(f"\nОбработано заметок: {processed}")
        print(f"Изменено заметок: {modified}")
        print(f"Всего добавлено ссылок: {self.changes_made}")
        
    def run(self) -> None:
        """Запускает весь процесс создания ссылок."""
        print("=== Создатель ссылок Obsidian ===")
        print(f"Хранилище: {self.vault_path}")
        print(f"Режим: {'Пробный запуск' if self.dry_run else 'Применение изменений'}")
        print(f"Резервное копирование: {'Включено' if self.backup else 'Отключено'}")
        print()
        
        if not self.vault_path.exists():
            print(f"Ошибка: Путь {self.vault_path} не существует")
            return
            
        # Создаем резервную копию перед изменениями
        if not self.dry_run:
            self.create_backup()
            
        # Сканируем хранилище
        self.scan_vault()
        
        if not self.notes:
            print("Заметки не найдены")
            return
            
        # Обрабатываем все заметки
        self.process_all_notes()
        
        if self.dry_run:
            print("\n💡 Это был пробный запуск. Для применения изменений запустите скрипт с флагом --apply")
        else:
            print("\n✅ Обработка завершена!")


def main():
    """Главная функция с обработкой аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Автоматически создает wikilinks в хранилище Obsidian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python obsidian_link_creator.py content --dry-run          # Пробный запуск
  python obsidian_link_creator.py content --apply            # Применить изменения
  python obsidian_link_creator.py content --apply --no-backup # Без резервной копии
        """
    )
    
    parser.add_argument(
        'vault_path',
        help='Путь к папке хранилища Obsidian'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Показать изменения без их применения (по умолчанию)'
    )
    
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Применить изменения к файлам'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Не создавать резервную копию'
    )
    
    args = parser.parse_args()
    
    # Определяем режим работы
    dry_run = not args.apply
    backup = not args.no_backup
    
    # Создаем и запускаем обработчик
    creator = ObsidianLinkCreator(
        vault_path=args.vault_path,
        dry_run=dry_run,
        backup=backup
    )
    
    creator.run()


if __name__ == "__main__":
    main()
