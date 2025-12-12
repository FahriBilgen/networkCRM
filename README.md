# Network CRM

Network CRM is a graph-first CRM that lets you map people, goals, visions and projects, visualise the strength of their relationships, and receive AI-powered recommendations on who to involve for each initiative.

---

## Architecture at a Glance

| Layer      | Stack / Tools                                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------------------------- |
| Backend    | Java 21 → Spring Boot 3.5 → PostgreSQL 16 (pgvector) → LangChain4j + Ollama → Spring Security (JWT auth)      |
| Frontend   | React 19 → TypeScript → Vite → React Flow → Zustand → Axios                                                   |
| Operations | Docker / Docker Compose (db + backend + frontend + Ollama)                                                    |

```
.
��� backend-java/         # Spring Boot service
��� frontend/             # React SPA
��� docker-compose.yml    # db + backend + frontend + Ollama stack
��� proje.md              # Original product specification
��� test_api_comprehensive.ps1   # Live backend smoke test
��� README.md
```

---

## 1. Quick Start (Docker Compose)

> Requires Docker Desktop (or compatible environment). The stack now starts PostgreSQL, Ollama, the Spring Boot API and the production frontend build together.

1. Start everything (first run will automatically download the `all-minilm` embedding model, so give it a minute):
   ```
   docker-compose up -d --build
   ```
2. Visit the services:
   - Backend API → `http://localhost:8080`
   - Frontend SPA → `http://localhost:5173`
   - PostgreSQL   → `localhost:5432` (`networkcrm` DB, credentials in `docker-compose.yml`)

The backend runs with the `default` Spring profile. To point it to a different DB/AI provider, edit `backend-java/src/main/resources/application.properties` or mount a custom `application-dev.properties`.
---

## 2. Running the Backend Locally

### Prerequisites
- Java 21
- Maven 3.9+
- PostgreSQL 16 (with the `pgvector` extension enabled)
- Optional: Ollama instance for embeddings (defaults to `http://localhost:11434`)

### Environment configuration

Create `backend-java/src/main/resources/application-dev.properties` (already git-ignored) or export the following variables:

```
spring.datasource.url=jdbc:postgresql://localhost:5432/networkcrm
spring.datasource.username=postgres
spring.datasource.password=postgres
langchain4j.ollama.base-url=http://localhost:11434
langchain4j.ollama.embedding-model.model-name=all-minilm
app.jwtSecret=please-change-this-secret-and-keep-at-least-64-characters
```

### Build & run

```
cd backend-java
mvn clean package
mvn spring-boot:run   # or java -jar target/network-crm-0.0.1-SNAPSHOT.jar
```

The API listens on `http://localhost:8080/api`.

### Database update for embeddings

The latest backend stores LangChain embedding vektörlerini `nodes.embedding` kolonu içinde tutuyor. PostgreSQL tarafında bir defaya mahsus aşağıdaki komutu çalıştırarak `jsonb` kolonu ekleyin (pgvector kullanıyorsanız buna denk gelen `vector` tipini tercih edebilirsiniz):

```sql
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS embedding jsonb;
```

Hibernate zaten `spring.jpa.hibernate.ddl-auto=update` ile aynı kolonu yaratabiliyor, ancak üretim/veri dolu ortamlarda manuel `ALTER TABLE` ile ilerlemeniz önerilir.

### Ollama bağlantısı

Docker Compose senaryosunda `ollama/ollama` servisi network içinde yer alır, `all-minilm` modelini ilk açılışta kendisi indirir ve backend `LANGCHAIN4J_OLLAMA_BASE_URL=http://ollama:11434` değeriyle konuşur. Uygulamayı doğrudan host makinede çalıştırıyorsanız `application.properties` içindeki varsayılan `http://localhost:11434` adresi yeterli; farklı bir makine/port kullanıyorsanız bu değişkeni güncelleyip backend’i yeniden başlatmanız yeterlidir.
---

## 3. Running the Frontend Locally

### Prerequisites
- Node.js 20+
- npm 10+

### Configure API base URL

```
cp frontend/.env.example frontend/.env
```

Update `VITE_API_BASE_URL` if your backend runs on a different host/port.

### Install & start

```
cd frontend
npm install
npm run dev
```

Application will be served on `http://localhost:5173`. Production build: `npm run build`.

---

## 4. Testing & Smoke Checks

### Backend unit tests
```
cd backend-java
mvn test
```

### End-to-end API test

Use the scripted scenario to create a test user, insert nodes/edges, run queries and clean up:

```
.\test_api_comprehensive.ps1
```

If the user does not exist the script will sign it up automatically. Make sure the backend is running before executing.

### Frontend build verification
```
cd frontend
npm run build
```

---

## 5. Useful APIs (selected)

| Endpoint                               | Description                                             |
| -------------------------------------- | ------------------------------------------------------- |
| `POST /api/auth/signup`                | Register a user                                         |
| `POST /api/auth/signin`                | Obtain JWT token                                        |
| `GET /api/graph`                       | Full graph snapshot (nodes + edges)                     |
| `GET /api/graph/vision-tree`           | Hierarchical Vision → Goal → Project tree               |
| `GET /api/nodes/filter`                | Filter nodes by sector, tags, relationship strength etc |
| `POST /api/edges`                      | Create KNOWS / SUPPORTS / BELONGS_TO edge               |
| `POST /api/ai/goals/{id}/suggestions`  | AI recommendations for a goal                           |
| `POST /api/ai/goals/{id}/link-person`  | Persist AI suggestion as SUPPORTS edge                  |

Authentication: `Authorization: Bearer <token>`.

---

## 6. AI & Embeddings

- Embeddings are generated through LangChain4j pointing at Ollama (`all-minilm` by default).  
- If Ollama is unavailable, embeddings may be `null`; AI suggestions will then fall back to previously stored SUPPORTS edges.
- For production, configure Ollama endpoint and model via environment variables or `application.properties`.

---

## 7. Frontend Notes

- Uses mock data as a fallback when the backend is unreachable.
- Vision tree, graph canvas and AI panels automatically switch to live data once the API responds.
- Drag & drop, node edit, and link person to goal actions are wired to backend endpoints and respect authorization.
- Graph canvas now includes an Auto Layout button (ELK layered algorithm) to reflow nodes quickly.

---

## 8. Housekeeping

- Temporary helper files (`build.log`, `build.sh`, older test scripts) have been removed to keep the repository clean for release.
- Use `test_api_comprehensive.ps1` as the single source for backend smoke testing.
- `.gitignore` already excludes build artifacts such as `frontend/node_modules`, Maven `target/`, IDE caches, etc.

---

## 9. Troubleshooting

| Symptom                                    | Fix                                                                                          |
| ------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `401 Unauthorized` on API calls            | Ensure `Authorization` header is present; run `test_api_comprehensive.ps1` to validate auth. |
| Ollama embedding requests fail             | Confirm the Ollama service is running and `langchain4j.ollama.base-url` is reachable.         |
| PostgreSQL refuses connection              | Check credentials/port, ensure `pgvector` extension is installed.                             |
| Frontend still shows mock data             | Backend unreachable or `VITE_API_BASE_URL` misconfigured. Check browser console/network tab. |

If you need to reset your environment, stop containers (`docker-compose down -v`) and start again with fresh volumes.

---

Happy networking! 🎯
