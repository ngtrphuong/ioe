# Media configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Backup configuration
BACKUP_ROOT = os.path.join(BASE_DIR, 'backups')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

# Create necessary directories if they do not exist
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(BACKUP_ROOT, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True) 