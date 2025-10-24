# Sequence Diagram - Sfera Pulse System

```mermaid
sequenceDiagram
    participant User as 👤 Пользователь
    participant WebUI as 🌐 Web Interface<br/>(React Frontend)
    participant Backend as ⚙️ Backend API<br/>(FastAPI)
    participant SferaAPI as 🔗 Sfera API<br/>(External)
    participant GitDB as 📊 Git/DB<br/>(Repository Storage)

    Note over User, GitDB: Аутентификация пользователя
    User->>WebUI: 1. Ввод логина/пароля
    WebUI->>Backend: 2. POST /api/sfera/auth/login
    Backend->>SferaAPI: 3. POST /app/ppau/api/auth/login
    SferaAPI-->>Backend: 4. access_token + refresh_token
    Backend-->>WebUI: 5. Токены аутентификации
    WebUI-->>User: 6. Успешный вход в систему

    Note over User, GitDB: Получение списка проектов
    User->>WebUI: 7. Запрос списка проектов
    WebUI->>Backend: 8. GET /api/sfera/projects
    Backend->>SferaAPI: 9. GET /projects (с токеном)
    SferaAPI->>GitDB: 10. Запрос проектов из репозиториев
    GitDB-->>SferaAPI: 11. Список проектов
    SferaAPI-->>Backend: 12. JSON с проектами
    Backend-->>WebUI: 13. Данные проектов
    WebUI-->>User: 14. Отображение списка проектов

    Note over User, GitDB: Получение репозиториев проекта
    User->>WebUI: 15. Выбор проекта
    WebUI->>Backend: 16. GET /api/sfera/projects/{key}/repos
    Backend->>SferaAPI: 17. GET /projects/{key}/repos
    SferaAPI->>GitDB: 18. Запрос репозиториев проекта
    GitDB-->>SferaAPI: 19. Список репозиториев
    SferaAPI-->>Backend: 20. JSON с репозиториями
    Backend-->>WebUI: 21. Данные репозиториев
    WebUI-->>User: 22. Отображение репозиториев

    Note over User, GitDB: Получение коммитов (Pulse Dashboard)
    User->>WebUI: 23. Запрос последних коммитов
    WebUI->>Backend: 24. GET /api/pulse/last-commits
    Backend->>SferaAPI: 25. GET /projects/{key}/repos/{repo}/commits
    SferaAPI->>GitDB: 26. Запрос истории коммитов
    GitDB-->>SferaAPI: 27. Данные коммитов
    SferaAPI-->>Backend: 28. JSON с коммитами
    Backend-->>WebUI: 29. Обработанные данные коммитов
    WebUI-->>User: 30. Отображение Pulse Dashboard

    Note over User, GitDB: Получение WIP веток
    User->>WebUI: 31. Переход на WIP Dashboard
    WebUI->>Backend: 32. GET /api/pulse/wip-branches
    Backend->>SferaAPI: 33. GET /projects/{key}/repos/{repo}/branches
    SferaAPI->>GitDB: 34. Запрос веток репозитория
    GitDB-->>SferaAPI: 35. Список веток
    SferaAPI-->>Backend: 36. JSON с ветками
    Backend-->>WebUI: 37. Фильтрация WIP веток
    WebUI-->>User: 38. Отображение WIP Dashboard

    Note over User, GitDB: Получение Pull Requests
    User->>WebUI: 39. Запрос Pull Requests
    WebUI->>Backend: 40. GET /api/sfera/projects/{key}/repos/{repo}/pull-requests
    Backend->>SferaAPI: 41. GET /projects/{key}/repos/{repo}/pull-requests
    SferaAPI->>GitDB: 42. Запрос PR из репозитория
    GitDB-->>SferaAPI: 43. Данные Pull Requests
    SferaAPI-->>Backend: 44. JSON с PR
    Backend-->>WebUI: 45. Данные Pull Requests
    WebUI-->>User: 46. Отображение Pull Requests

    Note over User, GitDB: Обработка ошибок
    alt Ошибка аутентификации
        SferaAPI-->>Backend: 401 Unauthorized
        Backend-->>WebUI: Ошибка авторизации
        WebUI-->>User: Запрос повторного входа
    else Ошибка сети
        SferaAPI-->>Backend: Timeout/Connection Error
        Backend-->>WebUI: 502 Bad Gateway
        WebUI-->>User: Сообщение об ошибке сети
    else Ошибка данных
        GitDB-->>SferaAPI: Данные недоступны
        SferaAPI-->>Backend: 404 Not Found
        Backend-->>WebUI: Пустой результат
        WebUI-->>User: "Нет данных для отображения"
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
