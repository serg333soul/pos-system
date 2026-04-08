import os
import re
import shutil
from pathlib import Path

# --- КОНФІГУРАЦІЯ ---
OUTPUT_DIR = '_ai_context'
MAX_FILE_SIZE_KB = 150  
TRUNCATE_LINES = 0      

# Папки-ігнор (ДОДАНО OUTPUT_DIR сюди, щоб він не сканував сам себе)
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'venv', 'env', '.idea', '.vscode', 
    'dist', 'build', 'postgres_data', '.pytest_cache', 'alembic', 'migrations', 
    '.history', 'coverage', 'tmp', 'temp', 'logs', 'assets', 'images', 'fonts',
    OUTPUT_DIR
}

# Файли-ігнор
IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 
    '.DS_Store', 'context_packer.py', 
    'debug_db.py', 'debug_raw.py', '*.log', '*.sqlite', '*.db', 'favicon.ico',
    '.gitignore', '.dockerignore'
}

# Розширення, які ми читаємо
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.vue', '.html', '.css', '.scss', 
    '.yml', '.yaml', '.json', '.sql', '.dockerfile', '.sh', '.md', '.txt', 
    '.conf', '.ini', '.toml', '.env.example'
}

class ContextPacker:
    def __init__(self, root_dir='.'):
        self.root_dir = Path(root_dir)
        self.tree_structure = []
        self.dependencies = []
        self.architecture_map = []
        
        # 🔥 Словник для розділеного контенту
        self.categories = {
            "00_architecture_and_configs.txt": [],
            "01_frontend.txt": [],
            "02_product_service.txt": [],
            "03_customer_service.txt": [],
            "04_inventory_service.txt": [],
            "05_finance_service.txt": [],
            "99_other.txt": []
        }
        
        self.stats = {'files': 0, 'lines': 0, 'tokens_approx': 0}

    def _should_ignore_dir(self, dir_name):
        return dir_name in IGNORE_DIRS or dir_name.startswith('.')

    def _should_ignore_file(self, file_name):
        if file_name in IGNORE_FILES or file_name.startswith('.'):
            return True
        if any(file_name.endswith(ext.replace('*', '')) for ext in IGNORE_FILES if ext.startswith('*')):
            return True
        return Path(file_name).suffix not in ALLOWED_EXTENSIONS

    def _get_category_for_file(self, rel_path: Path) -> str:
        """Визначає, в який файл покласти контент на основі шляху"""
        parts = rel_path.parts
        
        # Якщо файл лежить у корені проекту (або це nginx)
        if len(parts) == 1 or "nginx" in parts:
            return "00_architecture_and_configs.txt"
        
        # Маршрутизація по мікросервісах
        top_folder = parts[0]
        if top_folder == "frontend": return "01_frontend.txt"
        if top_folder == "product_service": return "02_product_service.txt"
        if top_folder == "customer_service": return "03_customer_service.txt"
        if top_folder == "inventory_service": return "04_inventory_service.txt"
        if top_folder == "finance_service": return "05_finance_service.txt"
        
        return "99_other.txt"

    def _analyze_dependencies(self, filepath, content):
        name = filepath.name
        if name == 'docker-compose.yml':
            services = re.findall(r'^\s\s([a-z0-9_]+):\s*$', content, re.MULTILINE)
            self.dependencies.append(f"Docker Services: {', '.join(services)}")
        elif name == 'requirements.txt':
            libs = [line.split('==')[0] for line in content.split('\\n') if line and not line.startswith('#')]
            self.dependencies.append(f"Python Libs ({filepath.parent.name}): {', '.join(libs[:10])}...")
        elif name == 'package.json':
            import json
            try:
                data = json.loads(content)
                deps = list(data.get('dependencies', {}).keys())
                self.dependencies.append(f"JS/Vue Libs: {', '.join(deps)}")
            except: pass

    def _analyze_architecture(self, filepath, content):
        if filepath.suffix == '.py':
            classes = re.findall(r'^class\s+([A-Za-z0-9_]+)', content, re.MULTILINE)
            funcs = re.findall(r'^def\s+([A-Za-z0-9_]+)', content, re.MULTILINE)
            if classes or funcs:
                self.architecture_map.append(f"{filepath.as_posix()}")
                if classes: self.architecture_map.append(f"  Classes: {', '.join(classes)}")
                if funcs: self.architecture_map.append(f"  Funcs: {', '.join(funcs[:5])}{'...' if len(funcs)>5 else ''}")

    def build_tree(self):
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not self._should_ignore_dir(d)]
            level = root.replace(str(self.root_dir), '').count(os.sep)
            indent = ' ' * 4 * level
            self.tree_structure.append(f"{indent}📁 {os.path.basename(root)}/")
            
            for f in sorted(files):
                if not self._should_ignore_file(f):
                    self.tree_structure.append(f"{indent}    📄 {f}")

    def pack_project(self):
        print("🔍 Scanning project and routing files...")
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if not self._should_ignore_dir(d)]
            
            for file in files:
                if self._should_ignore_file(file):
                    continue
                    
                filepath = Path(root) / file
                rel_path = filepath.relative_to(self.root_dir)
                
                # Перевірка розміру
                if filepath.stat().st_size > MAX_FILE_SIZE_KB * 1024:
                    continue

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    content = "".join(lines)
                    self.stats['files'] += 1
                    self.stats['lines'] += len(lines)
                    self.stats['tokens_approx'] += len(content) // 4
                    
                    self._analyze_dependencies(filepath, content)
                    self._analyze_architecture(filepath, content)

                    # Форматування для AI
                    formatted_content = f"\\n<file path=\"{rel_path.as_posix()}\">\\n{content}\\n</file>\\n"
                    
                    # Визначаємо, в який файл це покласти
                    category = self._get_category_for_file(rel_path)
                    self.categories[category].append(formatted_content)
                    
                except Exception as e:
                    print(f"⚠️ Error reading {rel_path}: {e}")

    def save_to_files(self):
        # 1. Створюємо/очищаємо папку _ai_context
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        print(f"📦 Generating modular context in ./{OUTPUT_DIR}/ ...")

        # 2. Зберігаємо 00_architecture_and_configs.txt (Особливий файл із загальною інфою)
        arch_file = Path(OUTPUT_DIR) / "00_architecture_and_configs.txt"
        with open(arch_file, 'w', encoding='utf-8') as f:
            f.write("SYSTEM CONTEXT FILE (ARCHITECTURE & CONFIGS)\\n====================\\n\\n")
            f.write(f"📊 OVERALL PROJECT STATISTICS\\nFiles: {self.stats['files']} | Lines: {self.stats['lines']} | Tokens: ~{self.stats['tokens_approx']}\\n\\n")
            
            f.write("🌳 PROJECT TREE\\n===============\\n")
            f.write("\\n".join(self.tree_structure) + "\\n\\n")
            
            if self.dependencies:
                f.write("🛠 KEY DEPENDENCIES\\n====================\\n")
                f.write("\\n".join(self.dependencies) + "\\n\\n")
                
            if self.architecture_map:
                f.write("🗺 ARCHITECTURE MAP\\n==================\\n")
                f.write("\\n".join(self.architecture_map) + "\\n\\n")
                
            f.write("📦 CONFIG FILE CONTENTS\\n=======================\\n")
            f.write("".join(self.categories["00_architecture_and_configs.txt"]))

        # 3. Зберігаємо всі інші категорії (якщо там є файли)
        for cat_name, contents in self.categories.items():
            if cat_name == "00_architecture_and_configs.txt" or not contents:
                continue # Вже зберегли вище, або категорія порожня
                
            cat_file = Path(OUTPUT_DIR) / cat_name
            with open(cat_file, 'w', encoding='utf-8') as f:
                f.write(f"SYSTEM CONTEXT FILE: {cat_name.upper().replace('.TXT', '')}\\n")
                f.write("=========================================\\n")
                f.write("This file contains the source code for a specific microservice/module.\\n\\n")
                f.write("📦 FILE CONTENTS\\n================\\n")
                f.write("".join(contents))

        print("\\n" + "="*50)
        print(f"✅ DONE! Context successfully split and saved to: ./{OUTPUT_DIR}/")
        print("📁 Generated files:")
        for cat_name, contents in self.categories.items():
            file_path = Path(OUTPUT_DIR) / cat_name
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                print(f"   - {cat_name} ({size_kb:.1f} KB)")
        print("="*50)

if __name__ == '__main__':
    packer = ContextPacker()
    packer.build_tree()
    packer.pack_project()
    packer.save_to_files()