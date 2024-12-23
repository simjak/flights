# Flight Search Service

A Python-based Google Flights scraper that uses Protocol Buffers for data serialization.

## Features

- Protocol Buffer-based data serialization
- Airport code enum support with autocompletion
- Support for multiple trip types (one-way, round-trip)
- Passenger configuration (adults, children, infants)
- Seat class selection (economy, premium-economy, business, first)
- Stop limit configuration
- Price trend indicators (low/typical/high)

## Technical Stack

- FastAPI for REST API
- SQLAlchemy for database ORM
- PostgreSQL for data storage
- RabbitMQ for task queue
- Protocol Buffers for data serialization
- UV for dependency management

## Development

1. Setup development environment:
```bash
make setup
```

2. Build Docker images:
```bash
make build
```

3. Run services:
```bash
make run
```

4. Run tests:
```bash
make test
```

5. Run linters:
```bash
make lint
```

6. Format code:
```bash
make format
```

## License

MIT
