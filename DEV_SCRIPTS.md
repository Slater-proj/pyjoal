# PyJOAL - Interactive Development Scripts

This repository includes two versions of the interactive development script to build, test, and deploy PyJOAL locally.

## Available Scripts

### 🇺🇸 English Version: `local-dev-en.sh`
Complete English interface with all development tools.

### 🇫🇷 French Version: `local-dev.sh`  
Interface complète en français avec tous les outils de développement.

## Features

Both scripts provide the same functionality with an improved user experience:

### 🛠️ Core Features
- **Complete build** (clean + build + tests)
- **Docker build** only
- **Backend tests** (Python with pytest, flake8, black)
- **Frontend tests** (Node.js with TypeScript)
- **Application management** (start/stop/logs/status)
- **BitTorrent client updates** (automatic version fetching)
- **Environment cleanup** (Docker containers/images)
- **Complete setup** (clients + build + test + start)
- **Quick deployment** (Git clean + build + start)

### ✨ Enhanced User Experience
- **Flexible confirmations**: Accepts multiple input variants
  - English: `y`, `yes`, `n`, `no` (case insensitive)
  - French: `o`, `oui`, `n`, `non` (case insensitive)  
  - Cross-language: `y`/`yes` also work in French version
- **Re-prompting**: Invalid input shows error and asks again (no script exit)
- **Default values**: Empty input uses sensible defaults
- **Color-coded interface**: Clear visual feedback with colored messages
- **Comprehensive error handling**: Robust validation and fallbacks

### 🔒 Security & Configuration
- **Auto .env generation**: Secure random tokens created automatically
- **Git safety**: Multiple confirmations for destructive operations
- **Environment detection**: Automatic Python virtual environment handling
- **Prerequisite checking**: Validates Docker and dependencies

## Usage

Make the scripts executable:
```bash
chmod +x local-dev.sh local-dev-en.sh
```

Run the English version:
```bash
./local-dev-en.sh
```

Run the French version:
```bash
./local-dev.sh
```

## Menu Options

Both scripts provide 12 interactive menu options:

1. **🔧 Complete build** - Clean environment + build + tests  
2. **🐳 Docker build** - Build Docker image only
3. **🧪 Backend tests** - Python tests (pytest, flake8, black)
4. **🎨 Frontend tests** - TypeScript/React tests
5. **▶️ Start application** - Launch with docker-compose
6. **⏹️ Stop application** - Stop all containers
7. **📋 Show logs** - Real-time log monitoring
8. **📊 Application status** - Containers, images, and accessibility
9. **🔄 Update clients** - Refresh BitTorrent client definitions
10. **🧹 Clean environment** - Remove containers and images
11. **🧪 Complete setup** - Full workflow (clients + build + test + start)
12. **🚀 Quick deployment** - Advanced Git cleanup + build + start

## Advanced Git Cleanup (Option 12)

The quick deployment option includes sophisticated Git repository management:

- **Untracked files**: List and optionally remove with confirmation
- **Modified files**: Show changes and offer `git reset --hard` with warning
- **Configuration protection**: Warns about important files (.env, docker-compose.override.yml)
- **Granular control**: Separate confirmations for each operation
- **Safety defaults**: All destructive operations default to "no"

## Requirements

- Docker and Docker Compose
- Python 3.x (for backend features)
- Node.js and npm (for frontend features, optional)
- Git (for repository management)
- OpenSSL or /dev/urandom (for secure token generation)

## Environment Configuration

The scripts automatically generate a `.env` file with secure random values if one doesn't exist:

```env
SECRET_TOKEN=<secure-random-32-char-hex>
UI_PATH_PREFIX=<random-16-char-hex>
PORT=8080
# ... other configuration options
```

## Testing the Confirmation System

A test script is included to verify the improved confirmation handling:

```bash
chmod +x test-confirmation.sh
./test-confirmation.sh
```

This tests various input scenarios and demonstrates the flexible confirmation behavior.

## Development Notes

- Both scripts maintain feature parity
- Confirmation functions are designed to be user-friendly and forgiving
- Error handling provides clear feedback without abrupt exits
- Virtual environment detection works with or without python3-venv package
- All Docker operations include proper cleanup and status checking

The scripts prioritize user experience while maintaining safety through multiple confirmations for destructive operations.