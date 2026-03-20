# Cloud Backend Deployment

Deploy the MCP Knowledge Base cloud backend to your own AWS account.

## Prerequisites

- AWS CLI configured with credentials
- SAM CLI installed (`brew install aws-sam-cli`)
- Python 3.13+

## Architecture

4 CloudFormation stacks deployed in order:

1. **mcp-kb** — S3 bucket + Lambda functions + shared layer (SAM)
2. **mcp-kb-cognito** — Cognito User Pool + client_credentials OAuth
3. **mcp-kb-gateway** — AgentCore Gateway with JWT auth
4. **mcp-kb-targets** — 3 Lambda targets wired to the gateway

## Deploy

```bash
cd infra/
REGION=us-west-2  # or your preferred region
```

### Step 1: S3 + Lambdas

```bash
cp samconfig.example.toml samconfig.toml
# Edit samconfig.toml: set your region

sam build
sam deploy
```

### Step 2: Cognito

```bash
aws cloudformation deploy \
  --template-file cognito.yaml \
  --stack-name mcp-kb-cognito \
  --region $REGION \
  --parameter-overrides Env=dev
```

### Step 3: AgentCore Gateway

```bash
aws cloudformation deploy \
  --template-file gateway.yaml \
  --stack-name mcp-kb-gateway \
  --region $REGION \
  --parameter-overrides Env=dev \
  --capabilities CAPABILITY_NAMED_IAM
```

### Step 4: Gateway Targets

```bash
aws cloudformation deploy \
  --template-file targets.yaml \
  --stack-name mcp-kb-targets \
  --region $REGION \
  --parameter-overrides Env=dev
```

## Get Your Credentials

After deployment, retrieve the values needed for the local MCP server:

```bash
# Gateway URL
aws cloudformation describe-stacks --stack-name mcp-kb-gateway --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='GatewayUrl'].OutputValue" --output text

# Token URL
aws cloudformation describe-stacks --stack-name mcp-kb-cognito --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='TokenUrl'].OutputValue" --output text

# Client ID
aws cloudformation describe-stacks --stack-name mcp-kb-cognito --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='ClientId'].OutputValue" --output text

# Client Secret
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name mcp-kb-cognito --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name mcp-kb-cognito --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='ClientId'].OutputValue" --output text)
aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID --client-id $CLIENT_ID --region $REGION \
  --query "UserPoolClient.ClientSecret" --output text
```

## Teardown

Delete in reverse order:

```bash
aws cloudformation delete-stack --stack-name mcp-kb-targets --region $REGION
aws cloudformation delete-stack --stack-name mcp-kb-gateway --region $REGION
aws cloudformation delete-stack --stack-name mcp-kb-cognito --region $REGION
# Empty the S3 bucket first
BUCKET=$(aws cloudformation describe-stacks --stack-name mcp-kb --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='LessonsBucketName'].OutputValue" --output text)
aws s3 rm "s3://$BUCKET" --recursive --region $REGION
sam delete --stack-name mcp-kb --region $REGION --no-prompts
```

## Known Issues

- **Cognito client_credentials tokens lack `aud` claim** — the gateway's `AllowedAudience` must NOT be set. Only use `AllowedClients` and `AllowedScopes`.
- **Lambda targets require `CredentialProviderType: GATEWAY_IAM_ROLE`** — without this, target creation fails.
- **Tool names are prefixed** by the gateway: `{target-name}___{tool-name}` (e.g., `write-lesson___write_lesson`).
