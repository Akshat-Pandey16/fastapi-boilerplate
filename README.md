# FastAPI Boilerplate

A production-ready FastAPI boilerplate with async PostgreSQL, SQLAlchemy, and Alembic migrations. This template provides a solid foundation for building scalable REST APIs with modern Python practices.

## ✨ Features

- 🚀 **FastAPI** with async/await support and automatic API documentation
- 🐘 **PostgreSQL** with async SQLAlchemy ORM
- 📊 **Alembic** for database migrations
- 🔧 **Environment-based configuration** with type safety
- 📝 **Pydantic schemas** for request/response validation
- 🛡️ **CORS middleware** with configurable origins
- 📋 **CRUD operations** with pagination support
- 🏗️ **Modular architecture** with clear separation of concerns
- 🔍 **API documentation** with Swagger UI and ReDoc
- 🎯 **Production-ready** settings and configurations

## 🏗️ Project Structure

```
fastapi-boilerplate/
├── alembic/                # Database migrations
│   ├── versions/          # Migration files (auto-generated)
│   ├── env.py            # Alembic environment configuration
│   ├── script.py.mako    # Migration template
│   └── README            # Alembic readme
├── core/                   # Core application modules
│   ├── __init__.py
│   ├── config.py         # Centralized configuration
│   └── router.py         # Main router configuration
├── database/               # Database configuration
│   ├── __init__.py
│   └── session.py        # Async SQLAlchemy setup
├── models/                 # SQLAlchemy data models
│   ├── __init__.py       # Model imports and exports
│   ├── common_model.py   # Base model with common fields
│   └── user.py           # User-specific models (example)
├── schemas/                # Pydantic schemas
│   ├── __init__.py
│   └── user.py           # User request/response schemas (example)
├── utils/                  # Utility modules
│   ├── __init__.py
│   └── response_helpers.py # API helper functions
├── api/                   # API endpoints
│   ├── __init__.py
│   └── users.py          # User-related API endpoints (example)
├── main.py                # FastAPI application entry point
├── requirements.txt      # Python dependencies
├── alembic.ini           # Alembic configuration file
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore patterns
└── LICENSE               # License file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (local installation or Docker)

### Installation

#### Option 1: Using Make Commands (Recommended)

1. **Clone and setup the project:**
   ```bash
   git clone <your-repo-url>
   cd fastapi-boilerplate
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Setup PostgreSQL:**
   
   **Option A: Local PostgreSQL**
   - Install PostgreSQL locally
   - Create a user and database

   **Option B: Docker**
   ```bash
   docker run --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your database configuration
   ```

4. **Install dependencies and setup database:**
   ```bash
   make setup
   ```

5. **Start the API server:**
   ```bash
   make run
   ```

#### Option 2: Manual Commands

1. **Clone and setup the project:**
   ```bash
   git clone <your-repo-url>
   cd fastapi-boilerplate
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

2. **Setup PostgreSQL:**
   
   **Option A: Local PostgreSQL**
   - Install PostgreSQL locally
   - Create a user and database

   **Option B: Docker**
   ```bash
   docker run --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your database configuration
   ```

4. **Run initial migration:**
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

   **Or use the setup script:**
   ```bash
   python scripts/setup.py
   ```

5. **Start the API server:**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure your settings:

#### Database Configuration
```env
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=fastapi_db
DB_HOST=localhost
DB_PORT=5432
DB_ECHO=true
DB_POOL_PRE_PING=true
DB_POOL_RECYCLE=300
```

#### API Configuration
```env
API_TITLE=FastAPI Boilerplate
API_DESCRIPTION=A production-ready FastAPI boilerplate with async PostgreSQL
API_VERSION=1.0.0
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
```

#### CORS Configuration
```env
CORS_ALLOW_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*
```

#### Application Configuration
```env
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Environment-Specific Settings

The application automatically adjusts based on the `ENVIRONMENT` variable:

- **Development** (`ENVIRONMENT=development`):
  - API documentation enabled at `/docs` and `/redoc`
  - Auto-reload enabled if `API_RELOAD=true`
  - Database echoing enabled if `DB_ECHO=true`

- **Production** (`ENVIRONMENT=production`):
  - API documentation disabled for security
  - Auto-reload disabled regardless of `API_RELOAD` setting
  - More restrictive default settings

## 📚 API Documentation

Once the server is running, visit (in development mode):
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Note: Documentation is automatically disabled in production for security.

## 🔌 API Endpoints

The boilerplate includes example CRUD operations for users:

### Root Endpoints
- `GET /` - Root endpoint with API information and environment details

### User Management (prefix: `/api/v1/users`)
- `POST /api/v1/users/register` - Create new user
- `GET /api/v1/users/` - List all users (with pagination)
- `GET /api/v1/users/{user_id}` - Get user by ID
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user

## 🗄️ Database Schema

### Users Table (Example)
The `users` table includes:
- `id` (integer, primary key)
- `username` (string, unique, required)
- `email` (string, unique, required)
- `full_name` (string, optional)
- `is_active` (boolean, default: True)
- `is_superuser` (boolean, default: False)
- `created_at` (timestamp, auto-generated)
- `updated_at` (timestamp, auto-updated)

## 🔄 Database Migrations

This project uses Alembic for database migrations with async SQLAlchemy support.

### Migration Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Check migration status
alembic current

# Downgrade migrations
alembic downgrade -1
```

## 🛠️ Development

### Quick Setup

Use the Makefile for common development tasks:

```bash
make help          # Show all available commands
make setup         # Install dependencies and setup database
make run           # Start the development server
make migrate       # Apply database migrations
make clean         # Clean up cache files
```

Or use the setup script directly:

```bash
python scripts/setup.py
```

The setup process will:
- Check prerequisites (Python version, .env file)
- Install dependencies
- Create initial database migration
- Apply migrations to set up the database

### Adding New Models

1. Create model in `models/` directory
2. Export model in `models/__init__.py`
3. Add Pydantic schemas to `schemas/` directory
4. Create API endpoints in `api/` directory
5. Include router in `core/router.py`
6. Generate and run migrations:
   ```bash
   alembic revision --autogenerate -m "Add new model"
   alembic upgrade head
   ```

### Project Structure Guidelines

- **Models** (`models/`): SQLAlchemy ORM models
- **Schemas** (`schemas/`): Pydantic models for request/response validation
- **API** (`api/`): API endpoints and business logic
- **Core** (`core/`): Application configuration and main router
- **Database** (`database/`): Database connection and session management
- **Utils** (`utils/`): Helper functions and utilities

## 🚀 Production Deployment

For production deployment:

1. Set `ENVIRONMENT=production`
2. Configure proper database credentials
3. Set appropriate CORS origins instead of `*`
4. Set `DB_ECHO=false` for better performance
5. Configure proper logging levels
6. Use a production WSGI server like Gunicorn

Example production `.env`:
```env
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
DB_ECHO=false
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
LOG_LEVEL=WARNING
```

## 🐳 Docker Support

### Using Make Commands (Recommended)

The easiest way to run the application with Docker:

```bash
make docker-run    # Start with Docker Compose
make docker-logs   # View logs
make docker-stop   # Stop containers
```

### Using Docker Compose directly

```bash
# Start the application with PostgreSQL
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

### Using Docker directly

```bash
# Build the image
docker build -t fastapi-boilerplate .

# Run the container
docker run -p 8000:8000 fastapi-boilerplate
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [troubleshooting section](#troubleshooting)
2. Review the API documentation at `/docs`
3. Open an issue on GitHub

## 🔧 Troubleshooting

### Common Issues

**Database Connection Issues:**
- Ensure PostgreSQL is running
- Check database credentials in `.env` file
- Verify database exists

**Migration Issues:**
- Make sure all models are imported in `alembic/env.py`
- Check database connection before running migrations
- Review migration files in `alembic/versions/`

**Configuration Issues:**
- Check that `.env` file exists and has correct syntax
- Verify environment variable names match the expected format

**Port Already in Use:**
- Change `API_PORT` in `.env` file if 8000 is occupied
- Or kill the process using the port
