import os

# --- КОНФІГУРАЦІЯ ---

# Папки, які ми ПОВНІСТЮ ігноруємо (не заходимо всередину)
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'venv', 'env', '.idea', '.vscode', 
    'dist', 'build', 'postgres_data', '.pytest_cache', 'migrations'
}

# Файли, які ми ігноруємо (не показуємо в дереві і не читаємо)
IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'collect_code.py', '.DS_Store', 
    'pnpm-lock.yaml', 'poetry.lock', 'full_project_context.txt' # Ігноруємо сам файл результату
}

# Розширення файлів, код яких нам ПОТРІБЕН
# (Всі інші файли будуть показані в дереві, але їх вміст не буде зчитано)
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.vue', '.html', '.css', '.scss', 
    '.yml', '.yaml', '.json', '.sql', '.dockerfile', 
    '.sh', '.md', '.txt'
}

EXACT_FILES_TO_READ = {'Dockerfile', 'docker-compose.yml', 'requirements.txt', 'package.json'}

def get_size_format(b, factor=1024, suffix="B"):
    """Конвертує байти в читабельний формат (KB, MB, etc.)"""
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"

def get_project_tree(start_path='.'):
    """Генерує візуальне дерево проекту."""
    tree_output = []
    
    for root, dirs, files in os.walk(start_path):
        # Фільтруємо папки "на льоту"
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 4 * level
        folder_name = os.path.basename(root)
        if folder_name == '.':
            folder_name = os.path.basename(os.getcwd())
            
        tree_output.append(f"{indent}📂 {folder_name}/")
        
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if f not in IGNORE_FILES:
                tree_output.append(f"{subindent}📄 {f}")
                
    return "\n".join(tree_output)

def collect_project_code(output_file='full_project_context.txt'):
    print("⏳ Аналізую структуру проекту та збираю код...")
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # 1. ЗАПИСУЄМО СТРУКТУРУ ПРОЕКТУ
        outfile.write("="*50 + "\n")
        outfile.write("PROJECT STRUCTURE (TREE VIEW)\n")
        outfile.write("="*50 + "\n")
        outfile.write(get_project_tree('.'))
        outfile.write("\n\n" + "="*50 + "\n")
        outfile.write("FILE CONTENTS\n")
        outfile.write("="*50 + "\n\n")

        # 2. ЗАПИСУЄМО ВМІСТ ФАЙЛІВ
        file_count = 0
        for root, dirs, files in os.walk('.'):
            # Фільтруємо папки
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if file in IGNORE_FILES:
                    continue
                
                ext = os.path.splitext(file)[1]
                
                # Читаємо файл, тільки якщо він у списку дозволених
                if ext in ALLOWED_EXTENSIONS or file in EXACT_FILES_TO_READ:
                    file_path = os.path.join(root, file)
                    
                    # Записуємо заголовок файлу
                    outfile.write(f"\n{'-'*50}\n")
                    outfile.write(f"PATH: {file_path}\n")
                    outfile.write(f"{'-'*50}\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                            content = infile.read()
                            if not content.strip():
                                outfile.write("[EMPTY FILE]\n")
                            else:
                                outfile.write(content)
                                outfile.write("\n") 
                        file_count += 1
                    except Exception as e:
                        outfile.write(f"[ERROR READING FILE: {e}]\n")

    # --- ОТРИМАННЯ РОЗМІРУ ФАЙЛУ ---
    file_size = os.path.getsize(output_file)
    readable_size = get_size_format(file_size)

    print("-" * 40)
    print(f"✅ Готово! Збережено {file_count} файлів.")
    print(f"📁 Файл результату: {output_file}")
    print(f"📊 Розмір файлу: {readable_size}")
    print("-" * 40)
    
    # Попередження, якщо файл завеликий для чату
    if file_size > 10 * 1024 * 1024: # 10 MB
        print("⚠️ УВАГА: Файл досить великий (>10MB). Можливо, варто додати щось у IGNORE_DIRS.")

if __name__ == '__main__':
    collect_project_code()