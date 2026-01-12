import os

# --- НАЛАШТУВАННЯ ---
OUTPUT_FILE = 'full_project_context.txt'

# Папки, які МИ ІГНОРУЄМО (найважливіше для економії місця)
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', 'venv', '.idea', '.vscode', 
    'dist', 'build', 'coverage', 'tmp', 'logs', 'pg_data', 'redis_data'
}

# Файли, які МИ ІГНОРУЄМО (бо вони великі або не несуть логіки коду)
IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock',
    'context_packer.py', OUTPUT_FILE, '.DS_Store', 'favicon.ico'
}

# Розширення файлів, які ми ХОЧЕМО бачити (тільки код і конфіги)
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.vue', '.html', '.css', '.json', 
    '.yml', '.yaml', '.sql', '.conf', '.sh', '.md', '.txt', '.env.example'
}

def get_file_size_mb(file_path):
    return os.path.getsize(file_path) / (1024 * 1024)

def pack_project():
    project_content = ""
    root_dir = os.getcwd()
    file_count = 0
    
    print(f"🚀 Починаю сканування проєкту: {root_dir}")
    print(f"🚫 Ігнорую папки: {', '.join(IGNORE_DIRS)}")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Видаляємо ігноровані папки зі списку сканування
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for filename in filenames:
            if filename in IGNORE_FILES:
                continue
            
            ext = os.path.splitext(filename)[1]
            
            # Спеціальна перевірка: Dockerfile не має розширення, але він нам потрібен
            is_dockerfile = filename.startswith('Dockerfile')
            
            if ext in ALLOWED_EXTENSIONS or is_dockerfile:
                file_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(file_path, root_dir)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Додаємо розділювачі, щоб AI розумів де початок файлу
                    project_content += f"\n{'='*40}\n"
                    project_content += f"FILE: {rel_path}\n"
                    project_content += f"{'='*40}\n"
                    project_content += content + "\n"
                    
                    file_count += 1
                    print(f"  📄 Додано: {rel_path}")
                except Exception as e:
                    print(f"  ⚠️ Помилка читання {rel_path}: {e}")

    # Записуємо результат
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(project_content)
    
    # --- ЗВІТ ПРО РОЗМІР ---
    size_mb = get_file_size_mb(OUTPUT_FILE)
    print(f"\n✅ ГОТОВО! Оброблено файлів: {file_count}")
    print(f"📦 Результат збережено у: {OUTPUT_FILE}")
    print(f"📊 Розмір файлу: {size_mb:.2f} MB")
    
    if size_mb > 5.0:
        print("\n⚠️  УВАГА: Файл досить великий (> 5 MB).")
        print("   Можливо, ти захопив щось зайве (наприклад, файли БД або build).")
        print("   Перевір IGNORE_DIRS у скрипті.")
    elif size_mb > 1.0:
         print("\nℹ️  Нормальний розмір для середнього проєкту.")
    else:
         print("\n✨ Компактний розмір. Можна сміливо кидати в чат.")

if __name__ == "__main__":
    pack_project()