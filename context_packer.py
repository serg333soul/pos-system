import os
import datetime
from pathlib import Path

# --- КОНФІГУРАЦІЯ (DevOps Settings) ---
OUTPUT_FILE = 'full_project_context.txt'

# Папки-ігнор (Системні, кеші, історія, залежності)
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'venv', 'env', '.idea', '.vscode', 
    'dist', 'build', 'postgres_data', '.pytest_cache', 'migrations', 
    '.history', 'coverage', 'tmp', 'temp', 'logs'
}

# Файли-ігнор (Локи, конфіги редакторів, бінарники, сам скрипт)
IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 
    '.DS_Store', 'context_packer.py', OUTPUT_FILE, 
    'debug_db.py', '*.log', '*.sqlite', '*.db'
}

# Розширення для читання (Тільки текстові/код)
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.vue', '.html', '.css', '.scss', 
    '.yml', '.yaml', '.json', '.sql', '.dockerfile', '.sh', '.md', '.txt', 
    '.conf', '.ini', '.toml'
}

# Файли без розширення, які треба читати
EXACT_FILES_TO_READ = {
    'Dockerfile', 'docker-compose.yml', 'requirements.txt', 'package.json', 
    'Makefile', 'Procfile', '.gitignore', '.env.example', 'nginx.conf'
}

# Ліміт розміру одного файлу (щоб не читати бандли по 1MB) - 100 KB
MAX_FILE_SIZE_BYTES = 100 * 1024 

class ProjectPacker:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.stats = {"files": 0, "lines": 0, "extensions": {}}
        self.file_contents = []
        self.tree_structure = []

    def should_ignore(self, path):
        # Перевірка папок
        for part in path.parts:
            if part in IGNORE_DIRS:
                return True
        # Перевірка імені файлу
        if path.name in IGNORE_FILES:
            return True
        if path.name.startswith('.'): 
            if path.name not in EXACT_FILES_TO_READ and path.suffix not in ALLOWED_EXTENSIONS:
                return True
        return False

    def is_text_file(self, path):
        if path.name in EXACT_FILES_TO_READ:
            return True
        return path.suffix in ALLOWED_EXTENSIONS

    def get_readable_size(self, size_in_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} TB"

    def generate_tree(self):
        self.tree_structure.append(f"📂 {self.root_dir.name}/")
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            level = root.replace(str(self.root_dir), '').count(os.sep)
            indent = '    ' * (level + 1)
            subindent = '    ' * (level + 2)
            
            if root != str(self.root_dir):
                self.tree_structure.append(f"{indent}📂 {os.path.basename(root)}/")
            
            for f in sorted(files):
                file_path = Path(root) / f
                if not self.should_ignore(file_path):
                    marker = "📄"
                    if not self.is_text_file(file_path):
                        marker = "📦"
                    self.tree_structure.append(f"{subindent}{marker} {f}")

    def collect_content(self):
        print(f"🚀 Починаю сканування проекту: {self.root_dir}")
        
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in sorted(files):
                file_path = Path(root) / file
                
                if self.should_ignore(file_path):
                    continue
                
                if self.is_text_file(file_path):
                    try:
                        file_size = file_path.stat().st_size
                        if file_size > MAX_FILE_SIZE_BYTES:
                            self.add_file_entry(file_path, "[SKIPPED: FILE TOO LARGE]", file_size)
                            continue

                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines = len(content.splitlines())
                            ext = file_path.suffix or 'No Ext'
                            self.stats["files"] += 1
                            self.stats["lines"] += lines
                            self.stats["extensions"][ext] = self.stats["extensions"].get(ext, 0) + 1
                            
                            self.add_file_entry(file_path, content, file_size)
                            
                    except Exception as e:
                        print(f"⚠️ Помилка читання {file_path}: {e}")

    def add_file_entry(self, path, content, size):
        relative_path = path.relative_to(self.root_dir)
        header = (
            f"\n{'='*60}\n"
            f"FILE: {relative_path}\n"
            f"SIZE: {size} bytes\n"
            f"{'='*60}\n"
        )
        self.file_contents.append(header + content + "\n")

    def generate_stats_block(self):
        stats_text = [
            "==================================================",
            "📊 PROJECT STATISTICS (DEVOPS OVERVIEW)",
            "==================================================",
            f"Total Files Scanned: {self.stats['files']}",
            f"Total Lines of Code: {self.stats['lines']}",
            "Technique Breakdown:",
        ]
        sorted_exts = sorted(self.stats["extensions"].items(), key=lambda item: item[1], reverse=True)
        for ext, count in sorted_exts:
            stats_text.append(f"  - {ext:<10}: {count} files")
        stats_text.append("==================================================\n")
        return "\n".join(stats_text)

    def save(self):
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(self.generate_stats_block())
            f.write("==================================================\n")
            f.write("🌳 PROJECT STRUCTURE\n")
            f.write("==================================================\n")
            f.write("\n".join(self.tree_structure))
            f.write("\n\n")
            f.write("".join(self.file_contents))
            
        # --- ФІНАЛЬНИЙ ЗВІТ ---
        final_size = Path(OUTPUT_FILE).stat().st_size
        readable_size = self.get_readable_size(final_size)
        
        print("\n" + "="*50)
        print(f"✅ Успішно! Результат збережено в: {OUTPUT_FILE}")
        print(f"📊 Всього рядків коду: {self.stats['lines']}")
        print(f"⚖️  РОЗМІР ФАЙЛУ КОНТЕКСТУ: {readable_size}")
        
        # Попередження, якщо файл завеликий
        if final_size > 1.5 * 1024 * 1024: # 1.5 MB
            print("⚠️  УВАГА: Файл великий (>1.5MB). Краще видалити зайві файли або логи.")
        else:
            print("👍 Розмір ідеальний для завантаження в чат.")
        print("="*50)

if __name__ == "__main__":
    packer = ProjectPacker('.')
    packer.generate_tree()
    packer.collect_content()
    packer.save()