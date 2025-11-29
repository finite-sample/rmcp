HTTP Server Deployment Guide
============================

Learn how to deploy RMCP HTTP server for production use in various environments.

Deployment Options
------------------

RMCP HTTP server can be deployed using several approaches:

🚀 **Cloud Platforms**: Google Cloud Run, AWS Lambda, Azure Container Instances
🐳 **Docker**: Self-hosted containers with Docker Compose
☸️ **Kubernetes**: Scalable container orchestration
🖥️ **Traditional**: Direct installation on virtual machines

Google Cloud Run (Recommended)
-------------------------------

Google Cloud Run provides serverless, automatically scaling HTTP servers - ideal for RMCP.

Prerequisites
~~~~~~~~~~~~~

- Google Cloud Account with billing enabled
- Docker installed locally
- ``gcloud`` CLI installed and configured

Build and Deploy
~~~~~~~~~~~~~~~~~

1. **Clone Repository:**

   .. code-block:: bash

      git clone https://github.com/finite-sample/rmcp.git
      cd rmcp

2. **Build Docker Image:**

   .. code-block:: bash

      # Build optimized production image
      docker build -f docker/Dockerfile --target production -t rmcp:latest .

3. **Tag for Google Container Registry:**

   .. code-block:: bash

      # Replace PROJECT_ID with your Google Cloud project ID
      docker tag rmcp:latest gcr.io/PROJECT_ID/rmcp:latest

4. **Push to Registry:**

   .. code-block:: bash

      docker push gcr.io/PROJECT_ID/rmcp:latest

5. **Deploy to Cloud Run:**

   .. code-block:: bash

      gcloud run deploy rmcp-server \\
        --image gcr.io/PROJECT_ID/rmcp:latest \\
        --platform managed \\
        --region us-central1 \\
        --allow-unauthenticated \\
        --port 8000 \\
        --memory 2Gi \\
        --cpu 2 \\
        --max-instances 10 \\
        --set-env-vars RMCP_HTTP_HOST=0.0.0.0,RMCP_HTTP_PORT=8000

6. **Configure Custom Domain (Optional):**

   .. code-block:: bash

      gcloud run domain-mappings create \\
        --service rmcp-server \\
        --domain stats.yourdomain.com \\
        --region us-central1

Configuration Options
~~~~~~~~~~~~~~~~~~~~~~

Environment variables for Cloud Run deployment:

=========================  ===============================================
Variable                   Description
=========================  ===============================================
``RMCP_HTTP_HOST``         Host to bind (use "0.0.0.0" for Cloud Run)
``RMCP_HTTP_PORT``         Port to listen on (default: 8000)
``RMCP_LOG_LEVEL``         Logging level (INFO, DEBUG, WARNING, ERROR)
``RMCP_R_TIMEOUT``         R execution timeout in seconds (default: 300)
``RMCP_VFS_ENABLED``       Enable virtual file system (default: true)
=========================  ===============================================

**Example Cloud Run Configuration:**

.. code-block:: yaml

   apiVersion: serving.knative.dev/v1
   kind: Service
   metadata:
     name: rmcp-server
     annotations:
       run.googleapis.com/ingress: all
   spec:
     template:
       metadata:
         annotations:
           autoscaling.knative.dev/maxScale: "10"
           run.googleapis.com/cpu-throttling: "false"
       spec:
         containerConcurrency: 100
         containers:
         - image: gcr.io/PROJECT_ID/rmcp:latest
           ports:
           - containerPort: 8000
           env:
           - name: RMCP_HTTP_HOST
             value: "0.0.0.0"
           - name: RMCP_HTTP_PORT  
             value: "8000"
           - name: RMCP_LOG_LEVEL
             value: "INFO"
           resources:
             limits:
               cpu: "2"
               memory: "2Gi"

Docker Deployment
-----------------

Self-hosted deployment using Docker containers.

Production Docker Compose
~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``docker-compose.prod.yml``:

.. code-block:: yaml

   version: '3.8'
   
   services:
     rmcp-server:
       build:
         context: .
         dockerfile: docker/Dockerfile
         target: production
       ports:
         - "8000:8000"
       environment:
         - RMCP_HTTP_HOST=0.0.0.0
         - RMCP_HTTP_PORT=8000
         - RMCP_LOG_LEVEL=INFO
         - RMCP_R_TIMEOUT=300
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
         start_period: 40s
       
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf:ro
         - ./ssl:/etc/ssl/certs:ro
       depends_on:
         - rmcp-server
       restart: unless-stopped

**Nginx Configuration** (``nginx.conf``):

.. code-block:: nginx

   events {
       worker_connections 1024;
   }

   http {
       upstream rmcp {
           server rmcp-server:8000;
       }

       server {
           listen 80;
           server_name stats.yourdomain.com;
           return 301 https://$server_name$request_uri;
       }

       server {
           listen 443 ssl http2;
           server_name stats.yourdomain.com;
           
           ssl_certificate /etc/ssl/certs/server.crt;
           ssl_certificate_key /etc/ssl/certs/server.key;
           
           location / {
               proxy_pass http://rmcp;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }
           
           location /mcp/sse {
               proxy_pass http://rmcp;
               proxy_set_header Host $host;
               proxy_set_header Connection "";
               proxy_http_version 1.1;
               proxy_buffering off;
               proxy_cache off;
               chunked_transfer_encoding off;
           }
       }
   }

**Deploy:**

.. code-block:: bash

   docker-compose -f docker-compose.prod.yml up -d

Kubernetes Deployment
----------------------

Scalable deployment with Kubernetes orchestration.

Kubernetes Manifests
~~~~~~~~~~~~~~~~~~~~~

**Deployment** (``k8s/deployment.yaml``):

.. code-block:: yaml

   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: rmcp-server
     labels:
       app: rmcp-server
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: rmcp-server
     template:
       metadata:
         labels:
           app: rmcp-server
       spec:
         containers:
         - name: rmcp-server
           image: gcr.io/PROJECT_ID/rmcp:latest
           ports:
           - containerPort: 8000
           env:
           - name: RMCP_HTTP_HOST
             value: "0.0.0.0"
           - name: RMCP_HTTP_PORT
             value: "8000"
           - name: RMCP_LOG_LEVEL
             value: "INFO"
           resources:
             requests:
               cpu: "0.5"
               memory: "1Gi"
             limits:
               cpu: "2"
               memory: "2Gi"
           livenessProbe:
             httpGet:
               path: /health
               port: 8000
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /health
               port: 8000
             initialDelaySeconds: 5
             periodSeconds: 5

**Service** (``k8s/service.yaml``):

.. code-block:: yaml

   apiVersion: v1
   kind: Service
   metadata:
     name: rmcp-service
   spec:
     selector:
       app: rmcp-server
     ports:
     - protocol: TCP
       port: 80
       targetPort: 8000
     type: LoadBalancer

**Ingress** (``k8s/ingress.yaml``):

.. code-block:: yaml

   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: rmcp-ingress
     annotations:
       kubernetes.io/ingress.class: "nginx"
       cert-manager.io/cluster-issuer: "letsencrypt-prod"
   spec:
     tls:
     - hosts:
       - stats.yourdomain.com
       secretName: rmcp-tls
     rules:
     - host: stats.yourdomain.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: rmcp-service
               port:
                 number: 80

**Deploy:**

.. code-block:: bash

   kubectl apply -f k8s/

AWS Lambda Deployment
---------------------

Serverless deployment using AWS Lambda with API Gateway.

Prerequisites
~~~~~~~~~~~~~

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Docker installed for building Lambda images

Lambda Container Image
~~~~~~~~~~~~~~~~~~~~~~

Create ``Dockerfile.lambda``:

.. code-block:: dockerfile

   FROM public.ecr.aws/lambda/python:3.11

   # Install system dependencies
   RUN yum update -y && \\
       yum install -y gcc gcc-c++ make

   # Install R
   RUN yum install -y epel-release && \\
       yum install -y R

   # Copy requirements and install Python dependencies
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   # Copy application code
   COPY rmcp/ ${LAMBDA_TASK_ROOT}/rmcp/
   COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

   CMD ["lambda_handler.handler"]

**Lambda Handler** (``lambda_handler.py``):

.. code-block:: python

   import json
   import asyncio
   from rmcp.core.server import MCPServer
   from rmcp.transport.http import HTTPTransport

   server = None

   def handler(event, context):
       global server
       
       if server is None:
           # Initialize RMCP server
           server = MCPServer()
           transport = HTTPTransport()
           server.set_transport(transport)
       
       # Extract HTTP request details from Lambda event
       method = event.get('httpMethod', 'GET')
       path = event.get('path', '/')
       headers = event.get('headers', {})
       body = event.get('body', '')
       
       # Process request asynchronously
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       
       try:
           result = loop.run_until_complete(
               process_request(method, path, headers, body)
           )
           return result
       finally:
           loop.close()

   async def process_request(method, path, headers, body):
       # Handle MCP requests
       if path.startswith('/mcp') and method == 'POST':
           # Process MCP JSON-RPC request
           try:
               request_data = json.loads(body) if body else {}
               response = await server.handle_request(request_data)
               
               return {
                   'statusCode': 200,
                   'headers': {
                       'Content-Type': 'application/json',
                       'Access-Control-Allow-Origin': '*'
                   },
                   'body': json.dumps(response)
               }
           except Exception as e:
               return {
                   'statusCode': 500,
                   'headers': {'Content-Type': 'application/json'},
                   'body': json.dumps({'error': str(e)})
               }
       
       # Handle health check
       elif path == '/health':
           return {
               'statusCode': 200,
               'headers': {'Content-Type': 'application/json'},
               'body': json.dumps({'status': 'healthy', 'transport': 'Lambda'})
           }
       
       # Default response
       else:
           return {
               'statusCode': 404,
               'headers': {'Content-Type': 'application/json'},
               'body': json.dumps({'error': 'Not found'})
           }

**Deploy Script** (``deploy-lambda.sh``):

.. code-block:: bash

   #!/bin/bash
   
   # Build and push Docker image
   docker build -f Dockerfile.lambda -t rmcp-lambda .
   
   # Tag for ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
   
   docker tag rmcp-lambda:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rmcp-lambda:latest
   docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rmcp-lambda:latest
   
   # Create Lambda function
   aws lambda create-function \\
     --function-name rmcp-server \\
     --package-type Image \\
     --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/rmcp-lambda:latest \\
     --role arn:aws:iam::$AWS_ACCOUNT_ID:role/lambda-execution-role \\
     --timeout 300 \\
     --memory-size 2048

Traditional Server Deployment
------------------------------

Direct installation on virtual machines or bare metal servers.

System Requirements
~~~~~~~~~~~~~~~~~~~

- **OS**: Ubuntu 20.04+ / CentOS 8+ / Amazon Linux 2
- **Python**: 3.11 or higher
- **R**: 4.4.0 or higher  
- **Memory**: 2GB minimum, 8GB recommended
- **CPU**: 2 cores minimum, 4 cores recommended
- **Storage**: 10GB for system + datasets

Installation Steps
~~~~~~~~~~~~~~~~~~

1. **Install System Dependencies:**

   .. code-block:: bash

      # Ubuntu/Debian
      sudo apt update
      sudo apt install -y python3.11 python3.11-pip r-base build-essential curl nginx

      # CentOS/RHEL
      sudo yum update -y
      sudo yum install -y python3.11 python3.11-pip R gcc gcc-c++ make curl nginx

2. **Install RMCP:**

   .. code-block:: bash

      pip3.11 install rmcp[http]

3. **Create Service User:**

   .. code-block:: bash

      sudo useradd -r -s /bin/false rmcp
      sudo mkdir -p /opt/rmcp
      sudo chown rmcp:rmcp /opt/rmcp

4. **Create Systemd Service** (``/etc/systemd/system/rmcp.service``):

   .. code-block:: ini

      [Unit]
      Description=RMCP Statistical Analysis Server
      After=network.target

      [Service]
      Type=exec
      User=rmcp
      Group=rmcp
      WorkingDirectory=/opt/rmcp
      Environment=RMCP_HTTP_HOST=127.0.0.1
      Environment=RMCP_HTTP_PORT=8000
      Environment=RMCP_LOG_LEVEL=INFO
      ExecStart=/usr/local/bin/rmcp serve-http
      Restart=always
      RestartSec=10

      [Install]
      WantedBy=multi-user.target

5. **Start and Enable Service:**

   .. code-block:: bash

      sudo systemctl daemon-reload
      sudo systemctl enable rmcp
      sudo systemctl start rmcp

6. **Configure Nginx Reverse Proxy:**

   Create ``/etc/nginx/sites-available/rmcp``:

   .. code-block:: nginx

      server {
          listen 80;
          server_name stats.yourdomain.com;

          location / {
              proxy_pass http://127.0.0.1:8000;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_set_header X-Forwarded-Proto $scheme;
          }

          location /mcp/sse {
              proxy_pass http://127.0.0.1:8000;
              proxy_set_header Host $host;
              proxy_set_header Connection "";
              proxy_http_version 1.1;
              proxy_buffering off;
              proxy_cache off;
              chunked_transfer_encoding off;
          }
      }

   Enable the site:

   .. code-block:: bash

      sudo ln -s /etc/nginx/sites-available/rmcp /etc/nginx/sites-enabled/
      sudo nginx -t
      sudo systemctl restart nginx

Monitoring and Logging
-----------------------

Application Monitoring
~~~~~~~~~~~~~~~~~~~~~~~

**Health Checks:**

.. code-block:: bash

   # Basic health check
   curl -f http://localhost:8000/health

   # Detailed server info via MCP initialize
   curl -X POST http://localhost:8000/mcp \\
     -H "Content-Type: application/json" \\
     -H "MCP-Protocol-Version: 2025-11-25" \\
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"monitor","version":"1.0"}}}'

**Prometheus Metrics** (optional):

Install ``prometheus-client`` and add metrics endpoint:

.. code-block:: python

   from prometheus_client import Counter, Histogram, generate_latest

   # Add to HTTP transport
   @self.app.get("/metrics")
   async def metrics():
       return Response(content=generate_latest(), media_type="text/plain")

Log Management
~~~~~~~~~~~~~~

**Structured Logging:**

.. code-block:: bash

   # Configure log level via environment
   export RMCP_LOG_LEVEL=INFO

   # View logs (systemd)
   sudo journalctl -u rmcp -f

   # View logs (Docker)
   docker logs -f rmcp-server

**Log Rotation** (``/etc/logrotate.d/rmcp``):

.. code-block:: text

   /var/log/rmcp/*.log {
       daily
       missingok
       rotate 52
       compress
       delaycompress
       notifempty
       create 644 rmcp rmcp
       postrotate
           systemctl reload rmcp
       endscript
   }

Security Considerations
-----------------------

Network Security
~~~~~~~~~~~~~~~~

- **Firewall**: Only expose ports 80/443 externally
- **TLS**: Always use HTTPS in production
- **VPC**: Deploy in private subnets with load balancer

Application Security
~~~~~~~~~~~~~~~~~~~~

- **R Sandbox**: R code execution is isolated
- **File System**: Virtual file system restricts access
- **Package Control**: R package installation requires approval
- **Rate Limiting**: Prevents abuse and DoS attacks

Data Security
~~~~~~~~~~~~~

- **Encryption**: Data encrypted in transit (HTTPS)
- **Isolation**: Each session isolated from others
- **Logging**: Sensitive data not logged
- **Compliance**: Configure for GDPR/HIPAA as needed

Performance Tuning
-------------------

Server Configuration
~~~~~~~~~~~~~~~~~~~~

**Memory Settings:**

.. code-block:: bash

   # Increase R memory limit
   export R_MAX_VSIZE=4G

   # Configure Python memory
   export PYTHONHASHSEED=0

**CPU Settings:**

.. code-block:: bash

   # Limit R CPU usage
   export OMP_NUM_THREADS=2

**Connection Limits:**

.. code-block:: bash

   # Maximum concurrent sessions
   export RMCP_MAX_SESSIONS=100

Load Balancing
~~~~~~~~~~~~~~

For high-traffic deployments, use multiple instances:

.. code-block:: yaml

   # Docker Compose with multiple replicas
   services:
     rmcp-server:
       # ... configuration ...
       deploy:
         replicas: 3
         resources:
           limits:
             cpus: '2'
             memory: 2G

Backup and Recovery
-------------------

Configuration Backup
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Backup configuration
   tar -czf rmcp-config-$(date +%Y%m%d).tar.gz \\
     /etc/systemd/system/rmcp.service \\
     /etc/nginx/sites-available/rmcp \\
     ~/.rmcp/

Database Backup
~~~~~~~~~~~~~~~

RMCP is stateless - no persistent data to backup. User data is processed in-memory.

Disaster Recovery
~~~~~~~~~~~~~~~~~

1. **Infrastructure as Code**: Use Terraform/CloudFormation
2. **Container Images**: Tag and version Docker images  
3. **Configuration Management**: Store configs in version control
4. **Monitoring**: Set up alerts for service availability

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**R Package Installation Fails:**

.. code-block:: bash

   # Check R package dependencies
   R -e "install.packages('jsonlite')"

   # Verify CRAN mirror access
   R -e "options(repos = c(CRAN = 'https://cran.r-project.org/'))"

**Memory Issues:**

.. code-block:: bash

   # Increase container memory limits
   docker run -m 4g rmcp:latest

   # Monitor memory usage
   docker stats rmcp-server

**Network Connectivity:**

.. code-block:: bash

   # Check port accessibility
   netstat -tlnp | grep :8000

   # Test from external network
   curl -I http://your-server:8000/health

**Session Management:**

.. code-block:: bash

   # Clear expired sessions (if implemented)
   curl -X DELETE http://localhost:8000/admin/sessions

Production Checklist
--------------------

Pre-deployment
~~~~~~~~~~~~~~

- [ ] Load testing completed
- [ ] Security scan passed
- [ ] SSL certificates configured
- [ ] Monitoring setup complete
- [ ] Backup procedures tested

Deployment
~~~~~~~~~~

- [ ] Blue-green deployment strategy
- [ ] Database migrations (if any)
- [ ] Configuration updated
- [ ] Health checks passing
- [ ] Load balancer configured

Post-deployment
~~~~~~~~~~~~~~~

- [ ] Smoke tests passed
- [ ] Performance metrics normal
- [ ] Error rates acceptable
- [ ] User acceptance testing
- [ ] Documentation updated

🔗 **Additional Resources:**

- **Example Configurations**: https://github.com/finite-sample/rmcp/tree/main/deployments
- **Security Guide**: :doc:`../shared/security`
- **Performance Guide**: :doc:`../shared/performance`
- **Support**: https://github.com/finite-sample/rmcp/issues