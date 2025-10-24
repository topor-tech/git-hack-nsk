# Список рекомендованных API-методов

Рекомендуем использовать вот эти API из swagger, но остальные API тоже можете использовать, если это вам поможет

## ppsc-backend

| Описание                           |  Метод | URL                                                    |
|------------------------------------|-------:|--------------------------------------------------------|
| Запросить список проектов          |    GET | /projects                                              |
| Запросить информацию по проекту    |    GET | /projects/{projectKey}                                 |
| Запросить список репозиториев      |    GET | /projects/{projectKey}/repos                           |
| Запросить информации о репозитории |    GET | /projects/{projectKey}/repos/{repoName}                |
| Запросить список веток репозитория |    GET | /projects/{projectKey}/repos/{repoName}/branches       |
| Запросить список коммитов          |    GET | /projects/{projectKey}/repos/{repoName}/commits        |
| Запросить diff коммита             |    GET | /projects/{projectKey}/repos/{repoName}/commits/{sha1} |
