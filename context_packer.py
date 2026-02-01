import os
from pathlib import Path

# --- КОНФІГУРАЦІЯ (AI Optimized) ---
OUTPUT_FILE = 'full_project_context.txt'

# Ліміт розміру одного файлу (щоб не забивати контекст сміттям)
MAX_FILE_SIZE_KB = 100  # 100 КБ

# Папки-ігнор
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'venv', 'env', '.idea', '.vscode', 
    'dist', 'build', 'postgres_data', '.pytest_cache', 'migrations', 
    '.history', 'coverage', 'tmp', 'temp', 'logs', 'assets' # assets часто бінарні або великі
}

# Файли-ігнор
IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 
    '.DS_Store', 'context_packer.py', OUTPUT_FILE, 
    'debug_db.py', '*.log', '*.sqlite', '*.db', 'favicon.ico'
}

# Розширення
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.vue', '.html', '.css', '.scss', 
    '.yml', '.yaml', '.json', '.sql', '.dockerfile', '.sh', '.md', '.txt', 
    '.conf', '.ini', '.toml', '.env.example' # Додано .env.example
}

class ContextPacker:
    def __init__(self):
        self.project_root = Path('.')
        self.file_contents = []
        self.tree_structure = []
        self.stats = {'files': 0, 'lines': 0, 'tokens_approx': 0}
        self.extensions_stats = {}

    def should_ignore(self, path):
        # Перевірка папок
        for part in path.parts:
            if part in IGNORE_DIRS:
                return True
        
        # Перевірка файлів
        if path.name in IGNORE_FILES:
            return True
            
        # Перевірка розширення
        if path.suffix not in ALLOWED_EXTENSIONS and path.name != 'Dockerfile':
             # Спеціальний виняток для файлів типу .env.example
            if not path.name.endswith('.example'): 
                return True
            
        return False

    def get_readable_size(self, size_in_bytes):
        for unit in ['B', 'KB', 'MB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} GB"

    def generate_tree(self):
        # Генеруємо дерево для візуального розуміння структури
        for root, dirs, files in os.walk(self.project_root):
            # Фільтрація папок
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            level = root.replace(str(self.project_root), '').count(os.sep)
            indent = ' ' * 4 * level
            self.tree_structure.append(f"{indent}📂 {os.path.basename(root)}/")
            
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                if not self.should_ignore(Path(root) / f):
                    self.tree_structure.append(f"{subindent}📄 {f}")

    def scan_files(self):
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                file_path = Path(root) / file
                if self.should_ignore(file_path):
                    continue

                # Перевірка розміру (Safety fuse)
                file_size_kb = file_path.stat().st_size / 1024
                if file_size_kb > MAX_FILE_SIZE_KB:
                    print(f"⚠️ Skipped large file: {file_path} ({file_size_kb:.2f} KB)")
                    self.file_contents.append(
                        f'<file path="{file_path}">\n'
                        f'\n'
                        f'</file>\n'
                    )
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines_count = len(content.splitlines())
                        
                        self.stats['files'] += 1
                        self.stats['lines'] += lines_count
                        self.stats['tokens_approx'] += len(content) // 4
                        
                        ext = file_path.suffix or 'No Ext'
                        self.extensions_stats[ext] = self.extensions_stats.get(ext, 0) + 1

                        # === ОСНОВНА ЗМІНА: XML FORMAT ===
                        # Це дозволяє AI чітко бачити межі файлів
                        self.file_contents.append(
                            f'\n<file path="{file_path}">\n'
                            f'{content}\n'
                            f'</file>\n'
                        )
                        
                        print(f"✅ Packed: {file_path}")
                except Exception as e:
                    print(f"❌ Error reading {file_path}: {e}")

    def generate_ai_header(self):
        """Створює 'System Prompt' для AI на початку файлу"""
        header = []
        header.append("")
        header.append("")
        header.append("")
        header.append(f"")
        header.append("\n")
        return "\n".join(header)

    def generate_stats_block(self):
        stats_text = []
        stats_text.append("==================================================")
        stats_text.append("📊 PROJECT STATISTICS")
        stats_text.append("==================================================")
        stats_text.append(f"Total Files: {self.stats['files']}")
        stats_text.append(f"Total Lines: {self.stats['lines']}")
        stats_text.append(f"Approx Tokens: ~{self.stats['tokens_approx']}")
        stats_text.append("Extensions:")
        for ext, count in sorted(self.extensions_stats.items(), key=lambda x: x[1], reverse=True):
            stats_text.append(f"  - {ext:<10}: {count}")
        stats_text.append("==================================================\n")
        return "\n".join(stats_text)

    def save(self):
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # 1. Інструкція для AI
            f.write(self.generate_ai_header())
            
            # 2. Статистика для тебе
            f.write(self.generate_stats_block())
            
            # 3. Дерево проекту (Карта)
            f.write("🌳 PROJECT STRUCTURE\n")
            f.write("==================================================\n")
            f.write("\n".join(self.tree_structure))
            f.write("\n\n")
            
            # 4. Контент файлів
            f.write("📦 FILE CONTENTS\n")
            f.write("==================================================\n")
            f.write("".join(self.file_contents))
            
        final_size = Path(OUTPUT_FILE).stat().st_size
        readable_size = self.get_readable_size(final_size)
        
        print("\n" + "="*50)
        print(f"✅ DONE! Context saved to: {OUTPUT_FILE}")
        print(f"📊 Lines: {self.stats['lines']}")
        print(f"⚖️  Size: {readable_size}")

if __name__ == '__main__':
    packer = ContextPacker()
    print("🚀 Starting AI Context Packer...")
    packer.generate_tree()
    packer.scan_files()
    packer.save()