"""
Base class for website generators.
"""

import os
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """
    Base class for website generators.
    
    Subclasses must implement generate_frontend(), generate_backend(), 
    generate_docker(), and generate_readme() methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the generator with configuration.
        
        Args:
            config: Dictionary containing:
                - output_dir: Directory to save generated files
                - model_path: Path to the trained model
                - model_type: Type of model (classifier, regressor, etc.)
                - labels: List of class labels
                - framework: ML framework (pytorch, keras, etc.)
                - website_type: Type of website to generate
                - frontend_framework: Frontend framework (vue, react, html)
                - backend_framework: Backend framework (flask, fastapi)
                - port: Backend port number
                - name: Website name
                - description: Website description
        """
        self.config = config
        self.output_dir = config.get('output_dir', '')
        self.model_path = config.get('model_path', '')
        self.model_type = config.get('model_type', '')
        self.labels = config.get('labels', [])
        self.framework = config.get('framework', 'pytorch')
        self.website_type = config.get('website_type', 'classification')
        self.frontend_framework = config.get('frontend_framework', 'vue')
        self.backend_framework = config.get('backend_framework', 'flask')
        self.port = config.get('port', 5000)
        self.name = config.get('name', 'Generated AI Website')
        self.description = config.get('description', '')
        self.profile = config.get('profile') or {}
        self.wizard = config.get('wizard') or {}
        self.generated_files: List[str] = []

    def get_site_title(self) -> str:
        return (self.wizard.get('siteName') or self.name or 'AI 识别系统').strip()

    def get_site_subtitle(self) -> str:
        if self.wizard.get('usageDescription'):
            return str(self.wizard['usageDescription']).strip()
        if self.profile.get('scenario'):
            return str(self.profile['scenario']).strip()
        return (self.description or 'AI-powered recognition service').strip()

    def get_primary_color(self) -> str:
        color = (self.wizard.get('primaryColor') or '').strip()
        if color and re.match(r'^#[0-9A-Fa-f]{6}$', color):
            return color
        tone = (self.profile.get('ui_tone') or '')
        if tone == 'alert_red':
            return '#ef4444'
        if tone == 'industrial_warning':
            return '#f59e0b'
        if tone == 'quality_inspect':
            return '#06b6d4'
        return '#f59e0b'

    def get_upload_hint(self) -> str:
        hints = self.profile.get('copy_hints') or []
        if hints:
            return str(hints[0])
        return '点击或拖拽上传图片进行识别'

    def get_db_engine(self) -> str:
        from ..site_factory.db_templates import normalize_db_engine
        env_cfg = self.config.get('environment_config') or self.config.get('environmentConfig') or {}
        raw = (
            self.config.get('dbEngine')
            or self.config.get('db_engine')
            or env_cfg.get('dbEngine')
            or env_cfg.get('db_engine')
            or 'mysql'
        )
        return normalize_db_engine(raw)

    def write_db_scaffold(self, extra_sql: str = '', extra_sql_mysql: str = '') -> List[str]:
        """Write schema.sql + init_db.py for configured DB engine."""
        from ..site_factory.db_templates import get_schema_sql, get_init_db_py
        engine = self.get_db_engine()
        files = []
        schema = get_schema_sql(engine)
        extra = extra_sql_mysql if engine == 'mysql' and extra_sql_mysql else extra_sql
        if extra:
            schema = schema.strip() + '\n' + extra.strip() + '\n'
        files.append(self._write_file('backend/db/schema.sql', schema))
        files.append(self._write_file('backend/db/init_db.py', get_init_db_py(engine)))
        files.append(self._write_file('backend/db/__init__.py', ''))
        return files

    def get_disclaimer_html(self) -> str:
        text = (self.wizard.get('disclaimer') or '').strip()
        if not text:
            return ''
        return f'<footer class="site-disclaimer">{text}</footer>'

    def get_modern_css_variables(self, primary: str = '') -> str:
        """Shared modern CSS scaffold for generated sites."""
        from .modern_templates import get_modern_css_block
        primary = primary or self.get_primary_color()
        return get_modern_css_block().replace('--site-primary, #f59e0b', primary)

    def generate(self) -> Dict[str, Any]:
        """
        Generate the complete website.
        
        Returns:
            Dictionary with:
                - success: Whether generation succeeded
                - generated_files: List of generated file paths
                - error: Error message if failed
        """
        try:
            # Validate output directory
            if not self.output_dir:
                return {'success': False, 'error': 'Output directory not specified'}

            # Create output directory structure
            self._prepare_output_directory()

            # Generate all components
            self._ensure_directory(self.output_dir)
            self._ensure_directory(os.path.join(self.output_dir, 'backend'))
            self._ensure_directory(os.path.join(self.output_dir, 'frontend'))

            # Generate backend files
            logger.info(f"Generating backend files for {self.website_type}")
            backend_files = self.generate_backend()
            self.generated_files.extend(backend_files)

            # Generate frontend files
            logger.info(f"Generating frontend files for {self.website_type}")
            frontend_files = self.generate_frontend()
            self.generated_files.extend(frontend_files)

            # Generate Docker configuration
            logger.info("Generating Docker configuration")
            docker_files = self.generate_docker()
            self.generated_files.extend(docker_files)

            # Generate README
            logger.info("Generating README")
            readme_files = self.generate_readme()
            self.generated_files.extend(readme_files)

            # Generate additional config files
            logger.info("Generating additional config files")
            config_files = self._generate_config_files()
            self.generated_files.extend(config_files)

            # Copy trained weights into backend/ so generated sites are self-contained
            copied_model = self._copy_model_weights_if_present()
            if copied_model:
                logger.info('Copied model weights to generated site: %s', copied_model)

            return {
                'success': True,
                'generated_files': self.generated_files,
                'output_dir': self.output_dir,
                'model_asset': copied_model or '',
            }

        except Exception as e:
            logger.exception(f"Website generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'generated_files': self.generated_files
            }

    def _prepare_output_directory(self) -> None:
        """Prepare the output directory structure."""
        # Create main directories
        self._ensure_directory(self.output_dir)
        self._ensure_directory(os.path.join(self.output_dir, 'backend'))
        self._ensure_directory(os.path.join(self.output_dir, 'frontend'))

    def _ensure_directory(self, path: str) -> None:
        """Ensure a directory exists, create if it doesn't."""
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.debug(f"Created directory: {path}")

    def _copy_model_weights_if_present(self) -> str:
        """Copy model_path into backend/ for portable generated sites."""
        import shutil

        src = (self.model_path or '').strip()
        if not src or not os.path.isfile(src):
            return ''

        dest_name = os.path.basename(src) or 'best.pt'
        dest = os.path.join(self.output_dir, 'backend', dest_name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        self.generated_files.append(dest)
        return dest_name

    def _write_file(self, relative_path: str, content: str) -> str:
        """
        Write content to a file in the output directory.
        
        Args:
            relative_path: Path relative to output_dir
            
        Returns:
            Full path to the created file
        """
        full_path = os.path.join(self.output_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.debug(f"Generated file: {full_path}")
        return full_path

    @abstractmethod
    def generate_frontend(self) -> List[str]:
        """
        Generate frontend code.
        
        Returns:
            List of generated file paths
        """
        pass

    @abstractmethod
    def generate_backend(self) -> List[str]:
        """
        Generate backend code.
        
        Returns:
            List of generated file paths
        """
        pass

    def generate_docker(self) -> List[str]:
        """
        Generate Docker configuration files.
        
        Returns:
            List of generated file paths
        """
        files = []
        
        # Dockerfile for backend
        dockerfile_content = self._get_dockerfile_content()
        files.append(self._write_file('Dockerfile', dockerfile_content))
        
        # docker-compose.yml
        compose_content = self._get_docker_compose_content()
        files.append(self._write_file('docker-compose.yml', compose_content))
        
        # .dockerignore
        dockerignore_content = self._get_dockerignore_content()
        files.append(self._write_file('.dockerignore', dockerignore_content))
        
        return files

    def generate_readme(self) -> List[str]:
        """
        Generate README.md with instructions.
        
        Returns:
            List of generated file paths
        """
        readme_content = self._get_readme_content()
        return [self._write_file('README.md', readme_content)]

    def _generate_config_files(self) -> List[str]:
        """Generate additional configuration files."""
        files = []
        
        # .env.example
        env_example = self._get_env_example_content()
        files.append(self._write_file('.env.example', env_example))
        
        config_path = os.path.join(self.output_dir, 'backend', 'config.json')
        config_data = {
            'model_path': os.path.basename(self.model_path),
            'labels': self.labels,
            'framework': self.framework,
            'website_type': self.website_type,
            'port': self.port,
            'db_engine': self.get_db_engine(),
            'required_features': self.config.get('required_features') or [],
            'model_artifact_manifest': self.config.get('model_artifact_manifest') or {},
        }
        if os.path.isfile(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as existing:
                    current = json.load(existing) or {}
                current.update({k: v for k, v in config_data.items() if v not in ('', [], {})})
                config_data = current
            except Exception:
                pass
        config_json = json.dumps(config_data, indent=2, ensure_ascii=False)
        files.append(self._write_file('backend/config.json', config_json))
        
        return files

    def _get_dockerfile_content(self) -> str:
        """Get Dockerfile content for the backend."""
        base_image = 'python:3.10-slim'
        
        return f'''# Generated AI Website Backend
# Built with Flowly-now Website Generator

FROM {base_image}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    libgomp1 \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ /app/

# Copy model file if exists
COPY backend/model.pth /app/model.pth 2>/dev/null || true

# Environment variables
ENV MODEL_PATH=/app/model.pth
ENV LABELS='{json.dumps(self.labels)}'
ENV PORT={self.port}

# Expose port
EXPOSE {self.port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{self.port}/health || exit 1

# Run the application
CMD ["python", "app.py"]
'''

    def _get_docker_compose_content(self) -> str:
        """Get docker-compose.yml content."""
        backend_port = self.port
        frontend_port = 3000
        db_engine = self.get_db_engine()
        mysql_service = ''
        mysql_depends = ''
        mysql_env = ''
        if db_engine == 'mysql':
            mysql_service = '''
  mysql:
    image: mysql:8.0
    container_name: ai_website_mysql
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_PASSWORD:-flowly_dev_password}
      - MYSQL_DATABASE=${MYSQL_DATABASE:-flowly_site}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped
'''
            mysql_depends = '''
      mysql:
        condition: service_healthy'''
            mysql_env = '''
      - DB_ENGINE=mysql
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_USER=root
      - MYSQL_PASSWORD=${MYSQL_PASSWORD:-flowly_dev_password}
      - MYSQL_DATABASE=${MYSQL_DATABASE:-flowly_site}'''

        return f'''version: '3.8'

services:
{mysql_service}
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ai_website_backend
    ports:
      - "{backend_port}:{backend_port}"
    environment:
      - MODEL_PATH=/app/model.pth
      - LABELS={json.dumps(self.labels)}
      - PORT={self.port}
{mysql_env}
    volumes:
      - ./backend:/app
      - model_data:/app/model
    depends_on:{mysql_depends if mysql_depends else ' []'}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{self.port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ai_website_frontend
    ports:
      - "{frontend_port}:80"
    depends_on:
      backend:
        condition: service_healthy
    environment:
      - VITE_API_URL=http://localhost:{backend_port}
    restart: unless-stopped

volumes:
  model_data:
  mysql_data:
'''

    def _get_dockerignore_content(self) -> str:
        """Get .dockerignore content."""
        return '''# Git
.git
.gitignore

# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
.venv
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.coverage
htmlcov/
*.test

# Misc
*.log
.DS_Store
Thumbs.db
node_modules/
'''

    def _get_env_example_content(self) -> str:
        """Get .env.example content."""
        return f'''# Model Configuration
MODEL_PATH=model.pth
LABELS={json.dumps(self.labels)}

# Server Configuration
PORT={self.port}
HOST=0.0.0.0

# Model Framework
FRAMEWORK={self.framework}

# Database Configuration
DB_ENGINE={self.get_db_engine()}
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=flowly_site

# Frontend API URL (used by frontend)
VITE_API_URL=http://localhost:{self.port}
'''

    def _get_readme_content(self) -> str:
        """Get README.md content - override in subclasses for specific content."""
        return f'''# {self.name}

{self.description}

## Model Information

- **Type**: {self.website_type.replace('_', ' ').title()}
- **Framework**: {self.framework.title()}
- **Labels**: {', '.join(self.labels) if self.labels else 'N/A'}

## Project Structure

```
.
├── backend/
│   ├── app.py           # Flask/FastAPI application with inference endpoint
│   ├── model_loader.py  # Model loading and prediction utilities
│   ├── requirements.txt # Python dependencies
│   └── config.json      # Model configuration
├── frontend/
│   ├── src/
│   │   └── App.vue      # Main application component
│   ├── package.json
│   └── vite.config.js
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

### Local Development

1. **Install backend dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp ../.env.example .env
   # Edit .env with your model path
   ```

3. **Start backend**:
   ```bash
   python app.py
   ```

4. **Install frontend dependencies** (in project root):
   ```bash
   cd frontend
   npm install
   ```

5. **Start frontend**:
   ```bash
   npm run dev
   ```

### Docker Deployment

1. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

2. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:{self.port}

## API Documentation

### POST /predict

Upload an image or data for prediction.

**Request**:
- Content-Type: `multipart/form-data`
- Body: `file` - The file to predict

**Response**:
```json
{{"boxes": [], "model_info": {{}}, "latency_ms": 12.5}}
```

### GET /health

Health check endpoint.

**Response**:
```json
{{"status": "healthy", "model_loaded": true}}
```

## Development Notes

- Ensure your trained model file is placed in the `backend/` directory
- Update `LABELS` in `.env` to match your model's classes
- The backend expects a model file compatible with {self.framework}

## License

Generated by Flowly-now Website Generator
'''
