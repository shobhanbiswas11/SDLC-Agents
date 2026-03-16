import os
import zipfile
from pathlib import Path

EXCLUDE_DIRS = {
    'node_modules', '__pycache__', '.git', '.next', 'dist', 
    'artifacts', '.venv', 'venv', '.pytest_cache', 
    'build', 'egg-info', '.egg-info'
}

EXCLUDE_FILES = {'.env', '.env.local', '*.pyc', '.DS_Store'}
EXCLUDE_EXTENSIONS = {'.pyc', '.pyo'}

def should_exclude(path):
    """Check if path should be excluded"""
    parts = Path(path).parts
    
    # Check if any part is in exclude dirs
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    
    # Check file extensions
    if any(path.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
        return True
    
    # Check file names
    if any(Path(path).name == f for f in EXCLUDE_FILES):
        return True
    
    return False

def create_clean_zip(source_dir, zip_name):
    """Create zip excluding unwanted files"""
    file_count = 0
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Remove excluded dirs from traversal
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                if not should_exclude(file_path):
                    # Arcname relative to source_dir (not current dir)
                    arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                    zipf.write(file_path, arcname)
                    file_count += 1
                    if file_count <= 10:  # Show first 10 files
                        print(f"Adding: {arcname}")
    
    return file_count

if __name__ == '__main__':
    source = '.'  # Current directory
    zip_name = 'code_generator_agent_clean.zip'
    
    # Remove old zip if exists
    if os.path.exists(zip_name):
        os.remove(zip_name)
    
    file_count = create_clean_zip(source, zip_name)
    
    if file_count > 0:
        print(f"\n✓ Zip created: {zip_name}")
        print(f"✓ Total files added: {file_count}")
    else:
        print("\n✗ No files were added! Check the source directory.")