"""Auto-generates a Dockerfile for a cloned repo that doesn't ship one, so
"Add Project" can go from a bare GitHub repo to a running container without
the developer having to hand-write deploy plumbing first.

Every generated Dockerfile listens on port 8000 (the fixed convention the
rest of the deploy pipeline - see vps_deploy.py - assumes). Detection covers
Django, Flask, FastAPI, Streamlit, Node (incl. frontend build step), PHP
(plain and Laravel), Ruby (plain and Rails), Go, and static HTML - the
stacks Origin Solutions' own and client projects actually show up as. A repo
with tooling this can't safely guess (e.g. Prisma/Postgres) should ship its
own Dockerfile - that always takes priority and is left untouched.

Two per-project overrides (set on Add Project / in a project's Advanced
settings) steer detection instead of replacing it outright:
  - main_file_path: the entry file/module to run, when a repo has more than
    one candidate or an unconventional layout (e.g. "src/app.py").
  - start_command: a full manual override. When set, auto-detection is
    skipped entirely - dependencies are still installed based on whichever
    manifest file is present, but the container's CMD is exactly this.
"""

import json
import os
import re


class DockerizeError(RuntimeError):
    pass


# Human-readable name for each stack detect_stack() can return, for the
# "we detected X" line in the new-web-app wizard.
STACK_LABELS = {
    "dockerfile": "Dockerfile in the repo (used as-is)",
    "manual": "Custom start command",
    "django": "Django",
    "streamlit": "Streamlit",
    "fastapi": "FastAPI",
    "node": "Node.js",
    "flask": "Flask",
    "php": "PHP",
    "ruby": "Ruby",
    "go": "Go",
    "static": "Static site (HTML/CSS/JS)",
}

DETECT_FAILED_MESSAGE = (
    "Could not auto-detect this project's stack. Set 'Main file path' "
    "or a full 'Start command' in Advanced settings, or add a "
    "Dockerfile to the repo root (it must listen on port 8000), and "
    "redeploy."
)


def detect_stack(repo_dir, main_file_path=None, start_command=None):
    """Which stack this checkout looks like, as a key of STACK_LABELS.

    Returns None when nothing matches. Writes nothing - the wizard calls
    this to show what it found before committing to a deploy, and
    ensure_dockerfile() dispatches on the same answer so the preview cannot
    drift from what actually gets built.
    """
    if os.path.isfile(os.path.join(repo_dir, "Dockerfile")):
        return "dockerfile"
    if start_command:
        return "manual"
    if os.path.isfile(os.path.join(repo_dir, "manage.py")):
        return "django"
    if _requirements_contains(repo_dir, "streamlit"):
        return "streamlit"
    if _requirements_contains(repo_dir, "fastapi"):
        return "fastapi"
    if os.path.isfile(os.path.join(repo_dir, "package.json")):
        return "node"
    if os.path.isfile(os.path.join(repo_dir, "requirements.txt")) and (
        main_file_path or _find_flask_entry(repo_dir)
    ):
        return "flask"
    if os.path.isfile(os.path.join(repo_dir, "composer.json")) or os.path.isfile(
        os.path.join(repo_dir, "index.php")
    ):
        return "php"
    if os.path.isfile(os.path.join(repo_dir, "Gemfile")):
        return "ruby"
    if os.path.isfile(os.path.join(repo_dir, "go.mod")):
        return "go"
    if os.path.isfile(os.path.join(repo_dir, "index.html")):
        return "static"
    return None


def ensure_dockerfile(repo_dir, main_file_path=None, start_command=None):
    """Writes a Dockerfile at the repo root if one isn't already there.
    Raises DockerizeError if the stack can't be confidently detected and no
    override was given."""
    stack = detect_stack(repo_dir, main_file_path, start_command)

    if stack == "dockerfile":
        return
    if stack == "manual":
        _write_manual(repo_dir, start_command)
    elif stack == "django":
        _write_django(repo_dir)
    elif stack == "streamlit":
        _write_streamlit(repo_dir, main_file_path)
    elif stack == "fastapi":
        _write_fastapi(repo_dir, main_file_path)
    elif stack == "node":
        _write_node(repo_dir)
    elif stack == "flask":
        _write_flask(repo_dir, main_file_path)
    elif stack == "php":
        _write_php(repo_dir)
    elif stack == "ruby":
        _write_ruby(repo_dir)
    elif stack == "go":
        _write_go(repo_dir, main_file_path)
    elif stack == "static":
        _write_static(repo_dir)
    else:
        raise DockerizeError(DETECT_FAILED_MESSAGE)


def _requirements_contains(repo_dir, package_name):
    path = os.path.join(repo_dir, "requirements.txt")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
    except OSError:
        return False
    return package_name.lower() in content


def _find_flask_entry(repo_dir):
    """Returns the module name (filename minus .py) of the first root-level
    .py file that looks like a Flask entrypoint (`app = Flask(` or
    `app = create_app()`), preferring app.py if it qualifies."""
    candidates = [f for f in os.listdir(repo_dir) if f.endswith(".py")]
    if "app.py" in candidates:
        candidates.remove("app.py")
        candidates.insert(0, "app.py")

    for filename in candidates:
        try:
            with open(os.path.join(repo_dir, filename), encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue
        if re.search(r"^app\s*=\s*(Flask\(|create_app\()", content, re.MULTILINE):
            return filename[:-3]
    return None


def _find_fastapi_entry(repo_dir):
    candidates = [f for f in os.listdir(repo_dir) if f.endswith(".py")]
    if "main.py" in candidates:
        candidates.remove("main.py")
        candidates.insert(0, "main.py")

    for filename in candidates:
        try:
            with open(os.path.join(repo_dir, filename), encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue
        if re.search(r"^app\s*=\s*FastAPI\(", content, re.MULTILINE):
            return filename[:-3]
    return None


def _find_streamlit_entry(repo_dir):
    for name in ("streamlit_app.py", "app.py", "main.py"):
        if os.path.isfile(os.path.join(repo_dir, name)):
            return name

    for filename in sorted(f for f in os.listdir(repo_dir) if f.endswith(".py")):
        try:
            with open(os.path.join(repo_dir, filename), encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue
        if re.search(r"^\s*(import streamlit|from streamlit)", content, re.MULTILINE):
            return filename
    return None


def _write_flask(repo_dir, main_file_path=None):
    if main_file_path:
        entry_module = main_file_path[:-3] if main_file_path.endswith(".py") else main_file_path
    else:
        entry_module = _find_flask_entry(repo_dir)
    if not entry_module:
        raise DockerizeError(
            "Found requirements.txt but couldn't locate a Flask app instance "
            "(expected `app = Flask(` or `app = create_app()`). Set 'Main "
            "file path' in Advanced settings and redeploy."
        )

    requirements_path = os.path.join(repo_dir, "requirements.txt")
    with open(requirements_path, encoding="utf-8", errors="ignore") as f:
        requirements = f.read().lower()
    extra_pip = "" if "gunicorn" in requirements else " gunicorn"

    # Older pinned pandas (<2.1) built against numpy 1.x segfaults/ValueErrors
    # under an unpinned numpy 2.x resolve - pin numpy first so pip's resolver
    # settles on a build pandas actually understands.
    numpy_guard = 'RUN pip install --no-cache-dir "numpy<2"\n' if "pandas" in requirements else ""

    dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
{numpy_guard}RUN pip install --no-cache-dir -r requirements.txt{extra_pip}
COPY . .
EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "{entry_module}:app"]
"""
    _write(repo_dir, dockerfile)


def _write_fastapi(repo_dir, main_file_path=None):
    if main_file_path:
        entry_module = main_file_path[:-3] if main_file_path.endswith(".py") else main_file_path
    else:
        entry_module = _find_fastapi_entry(repo_dir)
    if not entry_module:
        raise DockerizeError(
            "Found fastapi in requirements.txt but couldn't locate the "
            "FastAPI app instance (expected `app = FastAPI(` in a root .py "
            "file). Set 'Main file path' in Advanced settings and redeploy."
        )

    requirements_path = os.path.join(repo_dir, "requirements.txt")
    with open(requirements_path, encoding="utf-8", errors="ignore") as f:
        requirements = f.read().lower()
    extra_pip = "" if "uvicorn" in requirements else " uvicorn[standard]"

    dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt{extra_pip}
COPY . .
EXPOSE 8000
CMD ["uvicorn", "{entry_module}:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    _write(repo_dir, dockerfile)


def _write_streamlit(repo_dir, main_file_path=None):
    entry = main_file_path or _find_streamlit_entry(repo_dir)
    if not entry:
        raise DockerizeError(
            "Found streamlit in requirements.txt but couldn't guess the main "
            "file to run. Set 'Main file path' in Advanced settings (e.g. "
            "streamlit_app.py) and redeploy."
        )

    dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["streamlit", "run", "{entry}", "--server.port=8000", "--server.address=0.0.0.0", "--server.headless=true"]
"""
    _write(repo_dir, dockerfile)


def _write_django(repo_dir):
    package = _find_django_package(repo_dir)
    if not package:
        raise DockerizeError(
            "Found manage.py but couldn't locate the Django settings package "
            "(a directory containing settings.py and wsgi.py). Add a "
            "Dockerfile to the repo root and redeploy."
        )

    # A SQLite db.sqlite3 written under WORKDIR lives only in the container's
    # writable layer - gone on every redeploy (docker rm + a fresh
    # container). Repoint it at /data, which vps_deploy.py bind-mounts from a
    # persistent host directory, so the database survives redeploys instead
    # of silently resetting.
    settings_path = os.path.join(repo_dir, package, "settings.py")
    uses_sqlite = False
    try:
        with open(settings_path, encoding="utf-8", errors="ignore") as f:
            uses_sqlite = "sqlite3" in f.read()
    except OSError:
        pass
    sqlite_redirect = (
        f"RUN sed -i \"s|BASE_DIR / 'db.sqlite3'|'/data/db.sqlite3'|\" {package}/settings.py\n"
        if uses_sqlite else ""
    )

    dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn whitenoise
COPY . .

RUN sed -i 's/"django.middleware.security.SecurityMiddleware",/"django.middleware.security.SecurityMiddleware",\\n    "whitenoise.middleware.WhiteNoiseMiddleware",/' {package}/settings.py
RUN sed -i "s/ALLOWED_HOSTS = .*/ALLOWED_HOSTS = ['*']/" {package}/settings.py
{sqlite_redirect}RUN printf '\\nSTATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"\\nCSRF_TRUSTED_ORIGINS = ["https://*.originssolutions.com", "https://*.originsolutions.com"]\\nSECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")\\n' >> {package}/settings.py

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000
CMD python manage.py migrate --noinput && gunicorn -b 0.0.0.0:8000 {package}.wsgi:application
"""
    _write(repo_dir, dockerfile)


def _find_django_package(repo_dir):
    for name in os.listdir(repo_dir):
        full = os.path.join(repo_dir, name)
        if os.path.isdir(full) and os.path.isfile(os.path.join(full, "settings.py")) and os.path.isfile(
            os.path.join(full, "wsgi.py")
        ):
            return name
    return None


def _write_node(repo_dir):
    has_build_script = False
    package_json_path = os.path.join(repo_dir, "package.json")
    try:
        with open(package_json_path, encoding="utf-8") as f:
            pkg = json.load(f)
        has_build_script = "build" in pkg.get("scripts", {})
        if os.path.isdir(os.path.join(repo_dir, "prisma")):
            raise DockerizeError(
                "This Node project uses Prisma, which needs its own database "
                "provisioned - auto-deploy can't safely guess that. Add a "
                "Dockerfile (and a database) to the repo and redeploy."
            )
    except (OSError, ValueError):
        pass

    build_step = "RUN npm run build\n" if has_build_script else ""
    dockerfile = f"""FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
{build_step}EXPOSE 8000
ENV PORT=8000
CMD ["npm", "start"]
"""
    _write(repo_dir, dockerfile)


def _write_php(repo_dir):
    is_laravel = os.path.isfile(os.path.join(repo_dir, "artisan"))
    has_composer = os.path.isfile(os.path.join(repo_dir, "composer.json"))

    composer_install = (
        "RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer \\\n"
        "    && composer install --no-dev --optimize-autoloader --no-interaction\n"
    ) if has_composer else ""

    if is_laravel:
        run_cmd = '["php", "artisan", "serve", "--host=0.0.0.0", "--port=8000"]'
    else:
        docroot = "public" if os.path.isdir(os.path.join(repo_dir, "public")) else "."
        run_cmd = f'["php", "-S", "0.0.0.0:8000", "-t", "{docroot}"]'

    dockerfile = f"""FROM php:8.2-cli
RUN apt-get update && apt-get install -y --no-install-recommends git unzip libzip-dev \\
    && docker-php-ext-install pdo pdo_mysql zip \\
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
{composer_install}EXPOSE 8000
CMD {run_cmd}
"""
    _write(repo_dir, dockerfile)


def _write_ruby(repo_dir):
    is_rails = os.path.isfile(os.path.join(repo_dir, "config.ru"))
    run_cmd = (
        '["bundle", "exec", "rails", "server", "-b", "0.0.0.0", "-p", "8000"]'
        if is_rails
        else '["bundle", "exec", "rackup", "-o", "0.0.0.0", "-p", "8000"]'
    )

    dockerfile = f"""FROM ruby:3.2-slim
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev git \\
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY Gemfile* ./
RUN bundle install
COPY . .
EXPOSE 8000
CMD {run_cmd}
"""
    _write(repo_dir, dockerfile)


def _write_go(repo_dir, main_file_path=None):
    entry = main_file_path or "."
    dockerfile = f"""FROM golang:1.22-alpine AS build
WORKDIR /app
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN go build -o /server {entry}

FROM alpine:latest
COPY --from=build /server /server
EXPOSE 8000
ENV PORT=8000
CMD ["/server"]
"""
    _write(repo_dir, dockerfile)


def _write_static(repo_dir):
    nginx_conf = "server {\n    listen 8000;\n    root /usr/share/nginx/html;\n    index index.html;\n}\n"
    with open(os.path.join(repo_dir, "_autodeploy_nginx.conf"), "w", encoding="utf-8") as f:
        f.write(nginx_conf)

    dockerfile = """FROM nginx:alpine
COPY . /usr/share/nginx/html
COPY _autodeploy_nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8000
"""
    _write(repo_dir, dockerfile)


def _detect_base_and_install(repo_dir):
    """Best-effort dependency install step for the manual start_command
    override, based on whichever manifest file is present."""
    if os.path.isfile(os.path.join(repo_dir, "requirements.txt")):
        return "python:3.11-slim", "RUN pip install --no-cache-dir -r requirements.txt\n"
    if os.path.isfile(os.path.join(repo_dir, "package.json")):
        return "node:20-alpine", "RUN npm install\n"
    if os.path.isfile(os.path.join(repo_dir, "Gemfile")):
        return "ruby:3.2-slim", "RUN bundle install\n"
    if os.path.isfile(os.path.join(repo_dir, "go.mod")):
        return "golang:1.22-alpine", "RUN go mod download\n"
    return "python:3.11-slim", ""


def _write_manual(repo_dir, start_command):
    base_image, install_step = _detect_base_and_install(repo_dir)
    escaped_command = start_command.replace("\\", "\\\\").replace('"', '\\"')
    dockerfile = f"""FROM {base_image}
WORKDIR /app
COPY . .
{install_step}EXPOSE 8000
ENV PORT=8000
CMD ["sh", "-c", "{escaped_command}"]
"""
    _write(repo_dir, dockerfile)


def _write(repo_dir, dockerfile_text):
    with open(os.path.join(repo_dir, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write(dockerfile_text)
