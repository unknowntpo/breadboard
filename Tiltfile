# Tiltfile for Breadboard - Real-time Stock Dashboard

# Load namespace first
k8s_yaml('k8s/namespace.yml')

# Docker build with live reload
docker_build('breadboard-app',
  context='.',
  dockerfile='Dockerfile',
  live_update=[
    sync('backend/', '/app/backend/'),
    sync('dashboard/', '/app/dashboard/'),
    run('uv sync --frozen --no-dev', trigger=['pyproject.toml', 'uv.lock']),
  ]
)

# Docker build for Airflow (with baked DAGs)
docker_build('breadboard-airflow',
  context='.',
  dockerfile='airflow/Dockerfile'
)

# Load Kubernetes manifests
k8s_yaml(['k8s/clickhouse.yml', 'k8s/clickhouse-init.yml', 'k8s/app.yml'])

# Deploy Airflow via Helm
load('ext://helm_resource', 'helm_resource', 'helm_repo')

# Add Apache Airflow Helm repo
helm_repo('apache-airflow', 'https://airflow.apache.org')

# Deploy Airflow chart
helm_resource(
  'airflow',
  'apache-airflow/airflow',
  namespace='breadboard',
  flags=[
    '--values=k8s/airflow-values.yaml',
    '--set=images.airflow.repository=breadboard-airflow',
    '--set=images.airflow.tag=latest',
  ],
  image_deps=['breadboard-airflow'],
  image_keys=[('images.airflow.repository', 'images.airflow.tag')],
  resource_deps=['clickhouse-init'],
  port_forwards=['8080:8080'],
  labels=['workflow'],
)

# ClickHouse resource
k8s_resource('clickhouse',
  port_forwards=['9000:9000', '8123:8123'],
  labels=['core']
)

# ClickHouse init job
k8s_resource('clickhouse-init',
  resource_deps=['clickhouse'],
  labels=['core']
)

# Unified app resource (backend + dashboard)
k8s_resource('app',
  port_forwards=['8000:8000', '8501:8501'],
  resource_deps=['clickhouse-init'],
  labels=['core']
)

# Print access URLs
print("""
========================================
Breadboard Dashboard - Development Mode
========================================

Access your services at:
  • Dashboard:      http://localhost:8501
  • Backend API:    http://localhost:8000
  • API Docs:       http://localhost:8000/docs
  • ClickHouse:     http://localhost:8123
  • Airflow UI:     http://localhost:8080 (admin/admin)

Use 'tilt down' to stop all services
========================================
""")
