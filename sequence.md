# Sequence Diagram - Sfera Pulse System

```mermaid
sequenceDiagram
    participant User as User
    participant WebUI as Web Interface
    participant Backend as Backend API
    participant SferaAPI as Sfera API
    participant GitDB as Git/DB

    Note over User, GitDB: Authentication Flow
    User->>WebUI: 1. Enter login/password
    WebUI->>Backend: 2. POST /api/sfera/auth/login
    Backend->>SferaAPI: 3. POST /app/ppau/api/auth/login
    SferaAPI-->>Backend: 4. access_token + refresh_token
    Backend-->>WebUI: 5. Authentication tokens
    WebUI-->>User: 6. Login successful

    Note over User, GitDB: Get Projects List
    User->>WebUI: 7. Request projects list
    WebUI->>Backend: 8. GET /api/sfera/projects
    Backend->>SferaAPI: 9. GET /projects (with token)
    SferaAPI->>GitDB: 10. Query projects from repositories
    GitDB-->>SferaAPI: 11. Projects list
    SferaAPI-->>Backend: 12. JSON with projects
    Backend-->>WebUI: 13. Projects data
    WebUI-->>User: 14. Display projects list

    Note over User, GitDB: Get Project Repositories
    User->>WebUI: 15. Select project
    WebUI->>Backend: 16. GET /api/sfera/projects/{key}/repos
    Backend->>SferaAPI: 17. GET /projects/{key}/repos
    SferaAPI->>GitDB: 18. Query project repositories
    GitDB-->>SferaAPI: 19. Repositories list
    SferaAPI-->>Backend: 20. JSON with repositories
    Backend-->>WebUI: 21. Repositories data
    WebUI-->>User: 22. Display repositories

    Note over User, GitDB: Get Commits (Pulse Dashboard)
    User->>WebUI: 23. Request recent commits
    WebUI->>Backend: 24. GET /api/pulse/last-commits
    Backend->>SferaAPI: 25. GET /projects/{key}/repos/{repo}/commits
    SferaAPI->>GitDB: 26. Query commit history
    GitDB-->>SferaAPI: 27. Commits data
    SferaAPI-->>Backend: 28. JSON with commits
    Backend-->>WebUI: 29. Processed commits data
    WebUI-->>User: 30. Display Pulse Dashboard

    Note over User, GitDB: Get WIP Branches
    User->>WebUI: 31. Navigate to WIP Dashboard
    WebUI->>Backend: 32. GET /api/pulse/wip-branches
    Backend->>SferaAPI: 33. GET /projects/{key}/repos/{repo}/branches
    SferaAPI->>GitDB: 34. Query repository branches
    GitDB-->>SferaAPI: 35. Branches list
    SferaAPI-->>Backend: 36. JSON with branches
    Backend-->>WebUI: 37. Filter WIP branches
    WebUI-->>User: 38. Display WIP Dashboard

    Note over User, GitDB: Get Pull Requests
    User->>WebUI: 39. Request Pull Requests
    WebUI->>Backend: 40. GET /api/sfera/projects/{key}/repos/{repo}/pull-requests
    Backend->>SferaAPI: 41. GET /projects/{key}/repos/{repo}/pull-requests
    SferaAPI->>GitDB: 42. Query PR from repository
    GitDB-->>SferaAPI: 43. Pull Requests data
    SferaAPI-->>Backend: 44. JSON with PR
    Backend-->>WebUI: 45. Pull Requests data
    WebUI-->>User: 46. Display Pull Requests

    Note over User, GitDB: Error Handling
    alt Authentication Error
        SferaAPI-->>Backend: 401 Unauthorized
        Backend-->>WebUI: Authorization error
        WebUI-->>User: Request re-login
    else Network Error
        SferaAPI-->>Backend: Timeout/Connection Error
        Backend-->>WebUI: 502 Bad Gateway
        WebUI-->>User: Network error message
    else Data Error
        GitDB-->>SferaAPI: Data unavailable
        SferaAPI-->>Backend: 404 Not Found
        Backend-->>WebUI: Empty result
        WebUI-->>User: No data to display
    end
```

## Описание компонентов системы

### 👤 Пользователь
- Взаимодействует с веб-интерфейсом через браузер
- Вводит учетные данные для аутентификации
- Просматривает дашборды Pulse и WIP
- Выбирает проекты и репозитории для анализа

### 🌐 Web Interface (React Frontend)
- **Технологии**: React + TypeScript + Vite
- **Функции**:
  - Аутентификация пользователя
  - Отображение Pulse Dashboard (последние коммиты)
  - Отображение WIP Dashboard (рабочие ветки)
  - Выбор проектов и репозиториев
  - Обработка ошибок и состояний загрузки

### ⚙️ Backend API (FastAPI)
- **Технологии**: Python + FastAPI
- **Функции**:
  - Проксирование запросов к Sfera API
  - Аутентификация через Sfera платформу
  - Обработка и фильтрация данных
  - CORS поддержка для фронтенда
  - Обработка ошибок и таймаутов

### 🔗 Sfera API (External)
- **Функции**:
  - Аутентификация пользователей
  - Предоставление доступа к Git репозиториям
  - API для работы с проектами, репозиториями, коммитами
  - Управление Pull Requests и ветками

### 📊 Git/DB (Repository Storage)
- **Функции**:
  - Хранение Git репозиториев
  - История коммитов
  - Информация о ветках
  - Данные Pull Requests
  - Метаданные проектов
