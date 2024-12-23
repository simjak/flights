
# Design for Background Flight Search Service

## Overview

To handle long-running flight search processes that can take up to 2-3 days, we'll design a background service that:

* Runs asynchronously to prevent blocking the main API thread.
* Saves state periodically to allow resuming from crashes.
* Updates progress in real-time for UI tracking.

(Applied rule: Use asyncio for asynchronous operations)

## Components

### 1. API Layer (FastAPI)

* Search Endpoint: Accepts search parameters and initiates a background job.
* Input Validation: Validates incoming data against expected schema.
* Job ID Generation: Returns a unique job_id for tracking.
* Status Endpoint: Provides real-time progress based on job_id.

### 2. Background Worker

* Custom Asyncio-Based Worker: Implements a custom worker using asyncio to handle background tasks asynchronously.
* (Applied rule: Celery does not support asyncio, it should be a custom-made worker)
* Asynchronous Tasks: Performs flight searches without blocking.
* State Saving: Periodically saves progress to the database.
* Checkpointing: Stores current search index, found flights, and best price.
* Crash Recovery: On restart, resumes from the last saved state.
* Task Management: Manages tasks within an event loop for concurrency.
* Concurrency Control: Limits the number of concurrent searches based on max_concurrent_searches.
* Semaphore Mechanism: Controls access to limited resources.
* (Applied rule: Prefer iteration and modularization over code duplication)

### 3. Database Layer (PostgreSQL via SQLAlchemy)

* Job Table: Stores job details and progress.
* Fields: job_id, status, total_tasks, completed_tasks, found_flights, best_price, last_checkpoint, created_at, updated_at.
* Results Table: Stores found flights associated with a job_id.
* State Management: Keeps track of ongoing searches and their parameters.

### 4. Front-End/UI (Next.js Application)

* Progress Tracking: Polls the status endpoint to display real-time progress.
* Visual Indicators: Progress bars, current best price, and number of found flights.
* User Notifications: Alerts users upon completion or failure.
* Interactive UI: Allows users to initiate searches and view results dynamically.
* SEO Optimization: Utilizes Next.js features for improved SEO.
* Server-Side Rendering (SSR): Enhances performance and initial load times.
* Route Management: Manages client-side routing for a seamless user experience.
* (Applied rule: It will be a Next.js application, needs description)

## Workflow

* User Initiates Search:
* Sends a request to the search endpoint with parameters.
* API Creates Job:
* Generates job_id and saves initial job state to the database.
* Starts a background task using the custom asyncio worker.
* Background Worker Processes Task:
* Retrieves search parameters from the database.
* Begins the search loop, saving state after each iteration.
* (Applied rule: Implement proper error boundaries)
* Updates the job progress in the database.
* Crash Handling:
* On failure, the worker restarts and checks for incomplete jobs.
* Resumes processing from the last saved checkpoint.
* User Checks Progress:
* The Next.js app polls the status endpoint with job_id.
* Receives current progress and updates the UI.
* Completion:
* Once the search is complete, the final results are stored.
* User is notified, and results can be retrieved via the API.

## Key Considerations

* State Persistence:
* Use atomic transactions to prevent data corruption.
* Serialize state information efficiently for quick recovery.
* Scalability:
* Deploy multiple worker instances to handle higher loads.
* Optimize database queries for performance.
* Error Handling & Logging:
* Log errors with sufficient context for debugging.
* (Applied rule: Log errors appropriately for debugging)
* Provide meaningful error messages to the user.
* Security:
* Input Sanitization: Prevent injection attacks.
* (Applied rule: Sanitize user inputs)
* CORS Policies: Ensure only authorized domains can access the API.
* Content Security Policy: Implement CSP headers to mitigate XSS attacks.
* (Applied rule: Implement Content Security Policy)
* Testing:
* Unit Tests: For individual components like task scheduling and state saving.
* Integration Tests: To validate end-to-end workflow.
* (Applied rule: Implement E2E tests for critical flows)
* Performance Testing: Assess memory usage and optimize as needed.
* (Applied rule: Test memory usage and performance)

## Technologies & Tools

* Backend:
* FastAPI: For building API endpoints.
* Custom Asyncio Worker: For asynchronous background processing.
* SQLAlchemy: ORM for database interactions.
* Database:
* PostgreSQL: For reliable data storage.
* Asynchronous Programming:
* Asyncio: For non-blocking operations.
* Front-End/UI:
* Next.js: React framework for server-side rendering and static site generation.
* React: For building interactive user interfaces.
* Axios or Fetch API: For making HTTP requests to the backend.

## Repository Structure

fast-flights/
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml
├── setup.py
├── notebooks/
│   └── 00_flights.ipynb
├── fast_flights/
│   ├── __init__.py
│   ├── api.py          # API endpoints
│   ├── worker.py       # Custom asyncio-based worker tasks
│   ├── models.py       # Database models
│   ├── schemas.py      # Pydantic schemas
│   ├── utils.py        # Utility functions
│   ├── config.py       # Configuration settings
│   └── ...
└── frontend/
    └── nextjs-app/     # Next.js application for the front-end
        ├── pages/
        ├── components/
        ├── public/
        ├── styles/
        └── ...


## Documentation

* README.md:
* Instructions on setting up the environment.
* How to run the API, worker services, and the Next.js front-end.
* API Documentation:
* Endpoint descriptions with expected inputs and outputs.
* Authentication and authorization details.
* Code Comments:
* Only for complex logic where necessary.
* (Applied rule: Don't include comments unless it's for complex logic)
