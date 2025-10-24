# Sfera Pulse

A full-stack application for monitoring Git repositories and tracking work-in-progress (WIP) branches. The system provides real-time insights into project activity, recent commits, and branch status.

## Architecture

### Backend (`src/back/sfera_hack/`)
- **Framework**: FastAPI (Python)
- **Purpose**: REST API server that interfaces with Git repositories and provides data to the frontend
- **Key Features**:
  - Authentication system for Sfera platform
  - Commit history retrieval
  - WIP branch tracking
  
- **API Endpoints**:
  - `/api/sfera/` - Core Sfera platform integration (login, projects, commits, pull requests)
  - `/api/pulse/` - API for frontend
  - Health check and root endpoints

### Frontend (`src/front/sfera_pulse/`)
- **Framework**: React + TypeScript + Vite
- **Purpose**: Web interface for visualizing repository data and WIP branches
- **Key Features**:
  - User authentication with Sfera platform
  - **Pulse Dashboard**: View recent commits across projects and repositories
  - **WIP Dashboard**: Track work-in-progress branches
  - Project and repository selection
  - Real-time data updates
- **Components**:
  - `Pulse.tsx` - Main dashboard showing recent commits
  - `WIP.tsx` - Work-in-progress branch tracker
  - `ProjectRepositorySelector` - Project/repository selection interface
  - `Navbar` - Navigation component

## Local Development Setup

### Prerequisites
- Python 3.14+ with `uv` package manager
- Node.js 18+ with npm
- login + password for access to the repositories you want to monitor

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd src/back/sfera_hack
   ```

2. Install dependencies:
   ```bash
   uv pip compile pyproject.toml --output-file requirements.txt
   uv sync
   ```

3. Start the FastAPI development server:
   ```bash
   uv run fastapi dev .\sfera_hack\app.py
   ```

   The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd src/front/sfera_pulse
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

### Docker Setup (Alternative)

You can also run the entire application using Docker Compose:

```bash
# From the project root
docker-compose -f deploy/docker-compose.yml up --build
```

## Usage

1. **Access the Application**: Open `http://localhost:3000` in your browser
2. **Login**: Use your Sfera platform credentials
3. **Pulse Dashboard**: View recent commits across your projects
4. **WIP Dashboard**: Monitor work-in-progress branches
5. **Filter Data**: Use the project/repository selector to focus on specific repositories

## API Documentation

When the backend is running, you can access:
- **Interactive API docs**: `http://localhost:8000/docs`
- **Health check**: `http://localhost:8000/health`

## Project Structure

```
├── src/
│   ├── back/sfera_hack/          # FastAPI backend
│   │   ├── sfera_hack/
│   │   │   ├── api/              # API routes
│   │   │   │   ├── pulse/        # Repository management
│   │   │   │   └── sfera/        # Sfera platform integration
│   │   │   ├── connetors/        # External service connectors
│   │   │   └── core/             # Core business logic
│   │   └── app.py               # FastAPI application entry point
│   └── front/sfera_pulse/        # React frontend
│       ├── src/
│       │   ├── api/              # API client services
│       │   ├── components/       # React components
│       │   ├── Pulse.tsx         # Main dashboard
│       │   └── WIP.tsx           # WIP branch tracker
│       └── package.json
├── deploy/                       # Docker configuration
└── README.md
```

## Development Notes

- The backend uses CORS middleware to allow frontend connections
- Frontend uses React Router for navigation between Pulse and WIP dashboards
- Both components support URL parameters for state persistence
- The application is designed to work with the Sfera Git platform
