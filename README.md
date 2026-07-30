# Professional Discord Vouch Bot

An industry-level Discord bot for managing vouch/review systems with production-ready architecture.

## Features

- **Database Persistence**: SQLAlchemy ORM with async support (SQLite by default, PostgreSQL ready)
- **Configuration Management**: Pydantic-based configuration with environment variable validation
- **Service Layer Architecture**: Clean separation of business logic from bot commands
- **Comprehensive Logging**: Rotating file logs with structured formatting
- **Health Monitoring**: Built-in health checks and status tracking
- **Graceful Shutdown**: Proper resource cleanup on termination signals
- **Error Handling**: Global error handlers with detailed logging

## Project Structure

```
/workspace
├── main.py                 # Bot entry point and main class
├── config/
│   ├── __init__.py
│   └── settings.py         # Configuration management with Pydantic
├── database/
│   ├── __init__.py
│   └── connection.py       # Database connection manager
├── models/
│   ├── __init__.py
│   └── database_models.py  # SQLAlchemy ORM models
├── services/
│   ├── __init__.py
│   └── vouch_service.py    # Business logic layer
├── cogs/
│   ├── help.py             # Help command cog
│   └── vouch.py            # Vouch system cog (legacy, being migrated)
├── utils/
│   └── command_mentions.py # Dynamic command mention utility
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Installation

1. **Clone the repository** (or copy files)

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your Discord bot token
   ```

4. **Run the bot**:
   ```bash
   python main.py
   ```

## Configuration

Edit `.env` file with your settings:

```env
# Required
DISCORD_TOKEN=your_bot_token_here

# Optional
BOT_PREFIX=!
LOG_LEVEL=INFO
USE_SQLITE=true
BOT_ENVIRONMENT=development
```

See `.env.example` for all available options.

## Development

### Running Tests

```bash
pytest tests/ -v --cov
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint
ruff check .

# Type checking
mypy .
```

## Architecture

### Layers

1. **Bot Layer** (`main.py`, `cogs/`): Discord.py bot and command handlers
2. **Service Layer** (`services/`): Business logic independent of Discord
3. **Data Layer** (`models/`, `database/`): Database models and connections
4. **Configuration** (`config/`): Settings management

### Key Components

- **ProfessionalBot**: Main bot class with health monitoring and graceful shutdown
- **VouchService**: Business logic for vouch operations
- **DatabaseManager**: Async database connection pooling
- **BotSettings**: Validated configuration with Pydantic

## Migration from Legacy

The existing `cogs/vouch.py` uses JSON file storage. To migrate to the new database-backed system:

1. The new service layer is ready in `services/vouch_service.py`
2. Update `cogs/vouch.py` to use `VouchService` instead of JSON functions
3. Run database migrations (handled automatically on startup)

## Production Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### Environment Variables for Production

```env
BOT_ENVIRONMENT=production
LOG_LEVEL=WARNING
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
USE_SQLITE=false
```

## Monitoring

The bot includes built-in health checks:
- Database connectivity
- Discord connection status
- Command sync status

Check logs for health status updates every 30 seconds.

## License

MIT License - See LICENSE file for details.

## Support

For issues and feature requests, please open an issue on the repository.
