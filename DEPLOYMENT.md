# Deployment Guide

This guide covers deployment instructions for the Nifty 100 Financial Intelligence Platform on Render, Railway, and a standard VPS (Ubuntu/Debian).

## Environment Variables
Ensure the following environment variables are securely configured in your production environment:
- `DEBUG`: Must be set to `False` in production.
- `SECRET_KEY`: A complex, unpredictable string.
- `ALLOWED_HOSTS`: Your deployment domain(s) separated by commas (e.g., `api.example.com,example.com`).
- `DATABASE_URL`: Connection string for PostgreSQL (e.g., `postgresql://user:password@host:port/dbname`).
- `REDIS_URL`: Connection string for Redis (e.g., `redis://host:port/0`).

---

## 1. Deploying on Render (Platform as a Service)

We have provided a ready-to-use `render.yaml` Blueprint.

### Steps:
1. Connect your GitHub repository to Render.
2. In the Render Dashboard, click **New+** -> **Blueprint**.
3. Select your repository.
4. Render will automatically detect the `render.yaml` file and provision the following:
   - PostgreSQL Database
   - Redis Instance
   - Web Service (Gunicorn / Django)
   - Celery Worker (Background tasks)
   - Celery Beat (Task scheduler)
5. The `render.yaml` handles migrations and static file collection automatically via the `buildCommand`.

---

## 2. Deploying on Railway (Platform as a Service)

Railway provides an easy Docker-based deployment workflow.

### Steps:
1. Link your GitHub repository in the Railway Dashboard.
2. Railway will automatically detect the `Dockerfile` at the root (or `web_api/Dockerfile`).
3. Add **PostgreSQL** and **Redis** plugins to your project.
4. Go to the Variables tab of your web service and add the necessary environment variables. Use Railway's reference variables:
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   - `REDIS_URL` = `${{Redis.REDIS_URL}}`
5. **Set the Start Command** for the web service (if not picked up by Dockerfile):
   `gunicorn --bind 0.0.0.0:$PORT --chdir web_api core.wsgi:application`
6. **Deploy Workers:** Duplicate the service, but change the Start Command:
   - Worker: `celery -A core worker --chdir web_api -l info`
   - Beat: `celery -A core beat --chdir web_api -l info`

---

## 3. Deploying on a VPS (Ubuntu / Debian)

If you are deploying on a virtual private server (e.g., DigitalOcean, AWS EC2), you can use the provided `docker-compose.yml`.

### Prerequisites:
- Server with Ubuntu/Debian.
- Docker and Docker Compose V2 installed.
- Domain name pointed to the server's IP address.

### Steps:
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/nifty-financial-platform.git
   cd nifty-financial-platform
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env using nano or vim to set secure production values
   nano .env
   ```
   *Make sure `DEBUG=False` and `ALLOWED_HOSTS` includes your domain.*

3. **Start the Production Stack:**
   Run the stack in detached mode:
   ```bash
   docker compose up -d --build
   ```

4. **Run Initial Migrations (if necessary):**
   ```bash
   docker compose exec web python manage.py migrate
   ```

5. **Nginx & SSL (Optional but Recommended):**
   The current `docker-compose.yml` includes an Nginx container serving on port 80. For HTTPS, it is recommended to set up Certbot or use a reverse proxy like Traefik on the host machine to terminate SSL before passing traffic to port 80 of the Docker network.
