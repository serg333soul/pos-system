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
        Покращений парсер для пошуку сутностей FastAPI, SQLAlchemy, Pydantic та Vue 3.
        """
        symbols = []
        lines = content.splitlines()
        
        for line in lines:
            line_stripped = line.strip()
            
            # --- Python (FastAPI, SQLAlchemy, Pydantic) ---
            if file_ext == '.py':
                # Класи (з визначенням наслідування, напр. BaseModel)
                class_match = re.match(r'^class\s+([A-Za-z0-9_]+)(?:\(([^)]+)\))?:', line_stripped)
                if class_match:
                    class_name = class_match.group(1)
                    parent = class_match.group(2)
                    if parent and 'BaseModel' in parent:
                        symbols.append(f"📄 Schema: {class_name}")
                    elif parent and ('Base' in parent or 'Model' in parent):
                        symbols.append(f"🗄️ Model: {class_name}")
                    else:
                        symbols.append(f"📦 Class: {class_name}")
                
                # Роути FastAPI
                elif re.match(r'^@(router|app)\.(get|post|put|delete|patch)', line_stripped):
                    symbols.append(f"🌐 Endpoint: {line_stripped.split('(')[0]}")
                
                # Звичайні функції (ігноруємо приватні)
                elif line_stripped.startswith('def ') and not line_stripped.startswith('def _'):
                    symbols.append(f"ƒ  {line_stripped.split('(')[0].replace('def ', '')}")

            # --- JavaScript / TypeScript / Vue 3 ---
            elif file_ext in ['.js', '.vue', '.ts', '.jsx', '.tsx']:
                # Компоненти та класи
                if 'export default' in line_stripped:
                    symbols.append("📦 Default Export")
                
                # Vue 3: Props та Emits
                elif 'defineProps' in line_stripped:
                    symbols.append("📥 Props defined")
                elif 'defineEmits' in line_stripped:
                    symbols.append("📤 Emits defined")
                
                # Vue 3: Важливі стани та обчислення
                elif re.match(r'^(const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(ref|computed|reactive)\(', line_stripped):
                    var_name = line_stripped.split()[1]
                    type_match = re.search(r'(ref|computed|reactive)', line_stripped).group(1)
                    symbols.append(f"💾 State ({type_match}): {var_name}")
                
                # Функції
                elif line_stripped.startswith('function ') or 'const ' in line_stripped and '=>' in line_stripped:
                    # Простий пошук стрілочних функцій
                    func_match = re.match(r'const\s+([A-Za-z0-9_]+)\s*=\s*\(.*=>', line_stripped)
                    if func_match:
                        symbols.append(f"ƒ  {func_match.group(1)}")

        # Збільшимо ліміт до 15, оскільки інформація стала більш детальною
        return symbols[:15]

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

                # Визначаємо мову для атрибута lang (без крапки)
                lang = ext.replace('.', '') if ext else 'text'
                self.file_contents.append(
                    f"\n<file path=\"{file_path}\" lang=\"{lang}\">\n"
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