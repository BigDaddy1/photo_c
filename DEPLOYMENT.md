# PhotoColor Production Deployment Proposal

## Scope

This proposal describes the production environment for PhotoColor only. A separate test or staging environment is intentionally out of scope.

The goal is to run the service reliably on multiple Linux VPS or EC2 instances without Kubernetes or a PaaS platform. The design uses Docker, PostgreSQL, Nginx, Terraform, and GitHub Actions.

## Target Architecture

```text
Client
  |
  | HTTPS
  v
api.photocolor.com
  |
  v
Nginx (reverse proxy and load balancer)
  |
  +-- API instance 1 (PhotoColor Docker container)
  +-- API instance 2 (PhotoColor Docker container)
  +-- API instance N (PhotoColor Docker container)
             |
             +-- PostgreSQL
             +-- S3-compatible object storage
```

Nginx is the public entry point. It terminates TLS, forwards requests to the configured available API instances, applies request-size limits and rate limiting, and keeps the API servers private. Deployment health checks determine whether an updated instance is returned to the Nginx upstream.

The API is designed to be stateless. PostgreSQL stores image metadata, extracted palettes, and global RGB aggregates. Image files must be kept in shared object storage so that every API instance can serve the same files. Local Docker volumes remain suitable for development, but not for a multi-instance production deployment.

The existing `ImageStorageService` abstraction allows the local storage backend to be replaced with an S3-compatible backend without changing API endpoints.

## Infrastructure Management

Infrastructure is managed through Terraform. Terraform defines the VPS or EC2 instances, private network rules, firewall or security-group rules, static addresses, and DNS configuration in a repeatable form.

The initial production environment should contain:

- one Nginx instance;
- at least two API instances;
- one PostgreSQL instance in a private network;
- an S3-compatible object storage service.

The Nginx instance and PostgreSQL instance are initial single points of failure. They can be made redundant later if availability requirements justify the additional operational cost.

## API Processes and Capacity

An API instance is one running PhotoColor container on a server. A Uvicorn worker is a Python process inside that container.

For example, two API instances with two Uvicorn workers each provide four API processes in total. Nginx distributes incoming requests across the API instances; Uvicorn distributes work within an instance.

The number of workers is configured with an environment variable such as `UVICORN_WORKERS=2`. The final value should be selected through load testing because JPEG processing consumes CPU and memory. PostgreSQL connection-pool limits must also account for the total number of workers.

## Build and Release Delivery

GitHub Actions is responsible for continuous integration and delivery.

For each pull request, the pipeline should:

1. Install dependencies.
2. Run Ruff.
3. Run the test suite.
4. Verify that the Docker image builds successfully.

For a release, the pipeline should:

1. Run the same validation steps.
2. Build a versioned Docker image.
3. Publish the image to a container registry, such as GitHub Container Registry.
4. Run Alembic migrations once.
5. Update the production API instances to the approved image version.
6. Verify the `/health` endpoint after deployment.
7. Roll back to the previously approved image version if validation fails.

API servers pull the approved image from the registry; source code is not copied to production servers during deployment.

Alembic migrations must not run in every API container's startup command. A single release job runs them before the API instances are updated, preventing concurrent schema changes.

## Database and Backups

PostgreSQL is the source of truth for image records and colour statistics. It must not be publicly accessible and should accept connections only from API instances and trusted operational jobs.

The service needs daily PostgreSQL backups. If the required recovery-point objective is small, the backup strategy should also include write-ahead-log archival for point-in-time recovery. Object storage should use object versioning and lifecycle policies. Backup restoration should be tested regularly.

## Security

- Use HTTPS for all public traffic and redirect HTTP to HTTPS.
- Expose only Nginx ports 80 and 443 publicly.
- Keep API instances and PostgreSQL on a private network.
- Use SSH keys and restrict administrative access.
- Store database credentials, object-storage keys, registry credentials, and deployment keys in GitHub Secrets or a secret manager, never in Git.
- Use least-privilege database accounts.
- Keep operating systems and Docker images patched.
- Retain API upload-size limits, JPEG validation, and Nginx rate limiting.

## Observability

The API should emit structured logs to standard output. Container logs should be collected centrally. Logs should include request identifiers, HTTP method and path, status code, request duration, and unexpected-error tracebacks, but must not expose image contents or secrets.

Operational monitoring should cover request rate and latency, 4xx/5xx rates, image-processing duration, CPU and memory usage, disk capacity, PostgreSQL health, object-storage errors, and backup failures.

Alerts should be configured for unavailable health checks, increased 5xx responses, high latency, database failures, failed backups, low disk space, and sustained resource exhaustion.

## Implementation Sequence

1. Define production infrastructure with Terraform.
2. Provision Nginx, PostgreSQL, and at least two API instances.
3. Configure TLS, private networking, firewall rules, and DNS for `api.photocolor.com`.
4. Implement the S3-compatible `ImageStorageService` backend.
5. Publish versioned Docker images to a container registry.
6. Configure GitHub Actions for validation, migrations, deployment, health checks, and rollback.
7. Configure backups, centralized logging, monitoring, and alerting.
8. Run load, recovery, and deployment validation exercises before production use.
