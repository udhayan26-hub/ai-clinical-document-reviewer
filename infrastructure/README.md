# Infrastructure

Placeholder for future AWS deployment infrastructure. Local development uses the root-level `docker-compose.yml`; this directory is reserved for infrastructure-as-code and deployment tooling, kept isolated from application code.

- `aws/` — AWS infrastructure definitions (e.g. IaC templates, to be decided: CDK / Terraform / CloudFormation)
- `docker/` — shared/production Docker assets not specific to a single service
- `scripts/` — deployment and operational scripts

Nothing is deployed yet.
