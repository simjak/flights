# Implementation Plan for Flight Search Service

## Phase 1: Development Environment Setup

### Project Structure

```
flights/
├── docker/
│   ├── postgres/
│   │   └── init.sql
│   └── api/
│       └── Dockerfile
├── src/
│   ├── api/
│   ├── worker/
│   └── frontend/
├── tests/
├── alembic/
│   ├── versions/
│   └── alembic.ini
├── docker-compose.yml
├── .env
├── .env.example
├── pyproject.toml
├── uv.lock
└── README.md
```

### Dependencies Management (pyproject.toml)

```toml
[project]
name = "flights"
version = "0.1.0"
description = "Flight search service with background processing"
readme = "README.md"
requires-python = ">=3.12"

dependencies = [
    "fastapi==0.104.1",
    "uvicorn==0.24.0",
    "sqlalchemy==2.0.23",
    "alembic==1.12.1",
    "asyncpg==0.29.0",
    "pydantic[email]==2.5.2",
    "pydantic-settings==2.1.0",
    "python-jose[cryptography]==3.3.0",
    "python-multipart==0.0.6",
]

[dependency-groups]
dev = [
    "pytest==7.4.3",
    "pytest-asyncio==0.21.1",
    "pytest-cov==4.1.0",
    "black==23.11.0",
    "isort==5.12.0",
    "mypy==1.7.1",
    "ruff==0.1.6",
]
```

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: flights_user
      POSTGRES_PASSWORD: flights_password
      POSTGRES_DB: flights_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flights_user -d flights_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - flights-network

  pgadmin:
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@flights.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres
    networks:
      - flights-network

  api:
    build:
      context: .
      dockerfile: docker/api/Dockerfile
    environment:
      - DB_HOST=postgres
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - flights-network
    volumes:
      - ./src:/app/src
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

networks:
  flights-network:
    driver: bridge

volumes:
  postgres_data:
```

### Environment Variables

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=flights_user
DB_PASSWORD=flights_password
DB_NAME=flights_db
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true
API_CORS_ORIGINS=["http://localhost:3000"]
API_WORKERS=4

# Worker
WORKER_CONCURRENCY=3
MAX_RETRIES=3
CHECKPOINT_INTERVAL=300  # 5 minutes in seconds
WORKER_BATCH_SIZE=100

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Database Migration Setup (alembic.ini)

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://%(DB_USER)s:%(DB_PASSWORD)s@%(DB_HOST)s:%(DB_PORT)s/%(DB_NAME)s

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic
```

### Phase 2: Database Layer Implementation

### SQLAlchemy Models

```python
# jobs table
class Job(Base):
    job_id: str (UUID)
    status: str (pending/running/completed/failed)
    total_tasks: int
    completed_tasks: int
    found_flights: int
    best_price: float
    last_checkpoint: dict
    created_at: datetime
    updated_at: datetime

# results table
class FlightResult(Base):
    id: int
    job_id: str (FK to jobs)
    departure_airport: str
    destination_airport: str
    outbound_date: date
    return_date: date
    price: float
    airline: str
    stops: int
    duration: str
    current_price_indicator: str
```

### Database Service Layer

- Job management functions (create/update/delete)
- Result storage functions
- State persistence functions
- Progress tracking functions

## Phase 3: Background Worker Implementation

### Custom Asyncio Worker

1. Task queue management
2. State persistence
3. Progress tracking
4. Error handling and recovery
5. Concurrency control

### Checkpointing

- Save search state periodically
- Track completed combinations
- Store best prices found

## Phase 4: Frontend Implementation (Next.js)

### Pages

- Search form page
- Results page with real-time updates
- Flight details page

### Components

- Search form with validation
- Progress tracking component
- Results display with sorting/filtering
- Price trend indicators

### API Integration

- Search endpoint integration
- Progress polling
- Results fetching

## Phase 5: Testing and Documentation

### Unit Tests

- API endpoint tests
- Database operation tests
- Worker functionality tests
- Frontend component tests

### Integration Tests

- End-to-end search flow
- Error handling scenarios
- State recovery tests

### Documentation

- API documentation
- Setup instructions
- Deployment guide

## Implementation Order

1. Database Layer (highest priority)

   - Essential for state management
   - Required by both API and worker
2. Background Worker

   - Core functionality
   - State management
   - Error handling
3. API Enhancements

   - Job management endpoints
   - Progress tracking
   - Results retrieval
4. Frontend Development

   - User interface
   - Real-time updates
   - Result visualization
