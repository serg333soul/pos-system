import os
import re
from pathlib import Path

# --- КОНФІГУРАЦІЯ ---
OUTPUT_FILE = 'full_project_context.txt'
MAX_FILE_SIZE_KB = 150  # Трохи збільшив ліміт
TRUNCATE_LINES = 0      # 0 = не обрізати, >0 = лишати N рядків для великих файлів

# Папки-ігнор
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'venv', 'env', '.idea', '.vscode', 
    'dist', 'build', 'postgres_data', '.pytest_cache', 'migrations', 
    '.history', 'coverage', 'tmp', 'temp', 'logs', 'assets', 'images', 'fonts'
}

# Файли-ігнор
IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 
    '.DS_Store', 'context_packer.py', OUTPUT_FILE, 
    'debug_db.py', 'debug_raw.py', '*.log', '*.sqlite', '*.db', 'favicon.ico',
    '.gitignore', '.dockerignore'
}

# Розширення, які ми читаємо
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.vue', '.html', '.css', '.scss', 
    '.yml', '.yaml', '.json', '.sql', '.dockerfile', '.sh', '.md', '.txt', 
    '.conf', '.ini', '.toml', '.env.example'
}

class ProjectPacker:
    def __init__(self, root_dir='.'):
        self.root_dir = Path(root_dir)
        self.tree_structure = []
        self.file_contents = []
        self.architecture_map = [] # Список знайдених класів/функцій
        self.dependencies = []     # Вміст requirements/package.json
        self.stats = {
            'files': 0,
            'lines': 0,
            'tokens_approx': 0,
            'skipped_files': 0
        }
        self.extensions_stats = {}

    def is_ignored(self, path):
        # Перевірка папок
        for part in path.parts:
            if part in IGNORE_DIRS:
                return True
        
        # Перевірка імені файлу
        if path.name in IGNORE_FILES:
            return True
        
        # Перевірка розширення (якщо це файл)
        if path.is_file():
            if path.suffix == '.svg': return True # SVG завжди ігноруємо (шум)
            if path.suffix not in ALLOWED_EXTENSIONS and path.name not in {'Dockerfile', 'Makefile'}:
                return True
                
        return False

    def get_readable_size(self, size_in_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} TB"

    def extract_symbols(self, content, file_ext):
        """
        Дуже простий парсер для пошуку класів та функцій, 
        щоб AI міг швидко зрозуміти структуру файлу.
        """
        symbols = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            # Python
            if file_ext == '.py':
                if line.startswith('class '):
                    symbols.append(f"📦 {line.split('(')[0].replace(':', '')}")
                elif line.startswith('def ') and not line.startswith('def _'): # ігноруємо приватні
                    symbols.append(f"ƒ  {line.split('(')[0]}")
                elif 'APIRouter' in line and '=' in line:
                    symbols.append(f"🌐 Router: {line.split('=')[0].strip()}")
            
            # JS / Vue
            elif file_ext in ['.js', '.vue', '.ts']:
                if line.startswith('export default class'):
                    symbols.append(f"📦 Class: {line.split('class')[1].strip().split('{')[0]}")
                elif line.startswith('function '):
                    symbols.append(f"ƒ  {line.split('(')[0]}")
                elif 'const' in line and 'ref(' in line:
                    # Спроба знайти важливі стейти у Vue
                    var_name = line.split('const')[1].split('=')[0].strip()
                    symbols.append(f"💾 State: {var_name}")

        return symbols[:10] # Не більше 10 символів на файл, щоб не засмічувати карту

    def scan_directory(self):
        print(f"🚀 Scanning project in: {self.root_dir.resolve()}")
        
        for root, dirs, files in os.walk(self.root_dir):
            # Фільтрація папок in-place
            dirs[:] = [d for d in dirs if not self.is_ignored(Path(root) / d)]
            
            level = root.replace(str(self.root_dir), '').count(os.sep)
            indent = '    ' * level
            subindent = '    ' * (level + 1)
            
            folder_name = os.path.basename(root)
            if folder_name == '.': folder_name = self.root_dir.name
            
            self.tree_structure.append(f"{indent}📂 {folder_name}/")
            
            for f in sorted(files):
                file_path = Path(root) / f
                if self.is_ignored(file_path):
                    continue
                    
                self.tree_structure.append(f"{subindent}📄 {f}")
                self.process_file(file_path)

    def process_file(self, file_path):
        try:
            file_size_kb = file_path.stat().st_size / 1024
            
            if file_size_kb > MAX_FILE_SIZE_KB:
                self.stats['skipped_files'] += 1
                self.file_contents.append(
                    f"\n<file path=\"{file_path}\" status=\"skipped_too_large\">\n"
                    f"   \n"
                    f"</file>\n"
                )
                return

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Статистика
                lines_count = len(content.splitlines())
                self.stats['files'] += 1
                self.stats['lines'] += lines_count
                self.stats['tokens_approx'] += len(content) // 4
                
                ext = file_path.suffix
                self.extensions_stats[ext] = self.extensions_stats.get(ext, 0) + 1

                # 1. Витягуємо важливі залежності окремо
                if file_path.name in ['requirements.txt', 'package.json', 'docker-compose.yml']:
                    self.dependencies.append(f"\n--- {file_path.name} ---\n{content}\n")

                # 2. Будуємо карту символів (Архітектура)
                symbols = self.extract_symbols(content, ext)
                if symbols:
                    rel_path = file_path.relative_to(self.root_dir)
                    self.architecture_map.append(f"{rel_path}")
                    for s in symbols:
                        self.architecture_map.append(f"  └── {s}")

                # 3. Формуємо блок контенту з XML тегами
                # Якщо файл дуже великий, можна обрізати (опціонально)
                if TRUNCATE_LINES > 0 and lines_count > TRUNCATE_LINES:
                    content = "\n".join(content.splitlines()[:TRUNCATE_LINES])
                    content += f"\n... (Truncated remaining {lines_count - TRUNCATE_LINES} lines) ..."

                self.file_contents.append(
                    f"\n<file path=\"{file_path}\">\n"
                    f"{content}\n"
                    f"</file>\n"
                )

        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    def generate_ai_header(self):
        return (
            "# SYSTEM CONTEXT FILE\n"
            "# This file contains the full source code of the project.\n"
            "# USE THIS CONTEXT to understand architecture, debugging, and adding features.\n\n"
        )

    def save(self):
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # 1. Заголовок
            f.write(self.generate_ai_header())
            
            # 2. Статистика
            f.write("📊 PROJECT STATISTICS\n")
            f.write("=====================\n")
            f.write(f"Files: {self.stats['files']}\n")
            f.write(f"Lines: {self.stats['lines']}\n")
            f.write(f"Tokens: ~{self.stats['tokens_approx']}\n")
            f.write("\n")

            # 3. Ключові залежності (щоб AI одразу бачив стек)
            if self.dependencies:
                f.write("🛠 KEY DEPENDENCIES\n")
                f.write("====================\n")
                f.write("".join(self.dependencies))
                f.write("\n\n")

            # 4. Карта Архітектури (СУПЕР КОРИСНО ДЛЯ AI)
            if self.architecture_map:
                f.write("🗺 ARCHITECTURE MAP (Key Symbols)\n")
                f.write("================================\n")
                f.write("\n".join(self.architecture_map))
                f.write("\n\n")
            
            # 5. Дерево проекту
            f.write("🌳 PROJECT TREE\n")
            f.write("===============\n")
            f.write("\n".join(self.tree_structure))
            f.write("\n\n")
            
            # 6. Вміст файлів (XML wrapped)
            f.write("📦 FILE CONTENTS\n")
            f.write("================\n")
            f.write("".join(self.file_contents))
            
        final_size = Path(OUTPUT_FILE).stat().st_size
        print("\n" + "="*50)
        print(f"✅ DONE! Context saved to: {OUTPUT_FILE}")
        print(f"📊 Total Size: {self.get_readable_size(final_size)}")
        print("="*50)

if __name__ == "__main__":
    packer = ProjectPacker()
    packer.scan_directory()
    packer.save()