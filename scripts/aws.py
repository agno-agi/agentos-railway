#!/usr/bin/env python3
"""Provision AWS AgentCore sandboxes and S3 checkpoints for your agent platform."""

import base64
import json
import os
import re
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
import typer
from botocore.exceptions import BotoCoreError, ClientError, WaiterError  # type: ignore[import-untyped]
from dotenv import load_dotenv
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

ROOT = Path(__file__).resolve().parents[1]
# Local setup settings stay out of Git. Exported variables take precedence.
load_dotenv(ROOT / ".env", override=False)
AWS_PROFILE = os.getenv("AWS_PROFILE") or None
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or None
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "agentos-sandbox")
BUCKET_NAME = os.getenv("BUCKET_NAME", "")
CHECKPOINT_PREFIX = os.getenv("CHECKPOINT_PREFIX", "agentos/checkpoints/")

OWNER = "agno-template-sandbox"
console = Console()
app = typer.Typer(
    help=__doc__,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
)


@app.command()
def plan() -> None:
    """Resolve your AWS account and preview the resources without creating them."""
    with report_errors():
        validate_settings()
        deployment = SandboxDeployment()
        show_table(
            "AWS sandbox plan",
            {
                "Profile": deployment.profile,
                "Account": deployment.account,
                "Region": deployment.region,
                "Deployment": DEPLOYMENT_NAME,
                "Checkpoint bucket": deployment.bucket,
                "Checkpoint prefix": CHECKPOINT_PREFIX,
                "Image repository": DEPLOYMENT_NAME,
                "Runtime": runtime_name(),
            },
        )
        runtime = stack_outputs(deployment.get_stack(deployment.runtime_stack))
        show_table("Runtime observability", deployment.observability_status(runtime.get("RuntimeArn")))
        console.print("Creates ECR, an AgentCore runtime, a private S3 bucket, and scoped IAM permissions.")
        console.print("Enables runtime trace delivery and CloudWatch Transaction Search if needed.")
        console.print(
            "Transaction Search is shared by this account and region; existing indexing settings are preserved."
        )
        console.print("[dim]Read-only preview. Apply creates billable resources; it does not create access keys.[/dim]")


@app.command()
def apply() -> None:
    """Create or update the sandbox resources and upload the image."""
    with report_errors():
        validate_settings()
        deployment = SandboxDeployment()
        deployment.check_existing_stacks()
        run_docker("info", quiet=True)
        show_connection(deployment.provision(), deployment.region)


@app.command()
def status() -> None:
    """Show resource states and the configuration for your API."""
    with report_errors():
        validate_settings()
        deployment = SandboxDeployment()
        show_connection(deployment.inspect(), deployment.region)


def runtime_name() -> str:
    return DEPLOYMENT_NAME.replace("-", "_")


def validate_settings() -> None:
    """Catch configuration mistakes before connecting to AWS or starting Docker."""
    settings = {
        "AWS_REGION": (AWS_REGION or "", r"[a-z]{2}(?:-[a-z]+)+-[0-9]+"),
        "DEPLOYMENT_NAME": (DEPLOYMENT_NAME, r"[a-z][a-z0-9-]{0,31}"),
        "CHECKPOINT_PREFIX": (CHECKPOINT_PREFIX, r"[A-Za-z0-9][A-Za-z0-9_/-]*/"),
    }
    for name, (value, pattern) in settings.items():
        if not value and name == "AWS_REGION":
            continue
        if not re.fullmatch(pattern, value):
            raise ValueError(f"Set a valid {name} in .env or your shell environment.")
    validate_bucket(BUCKET_NAME)
    if not (ROOT / "Dockerfile").is_file():
        raise ValueError("The template Dockerfile must be present beside scripts/.")


def validate_bucket(name: str) -> None:
    if not name:
        return
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", name):
        raise ValueError("Set a valid BUCKET_NAME in .env or your shell environment.")
    if name.startswith(("xn--", "sthree-", "amzn-s3-demo-")) or name.endswith(("--x-s3", "--ol-s3", "--table-s3")):
        raise ValueError("BUCKET_NAME uses a reserved S3 prefix or suffix.")


class SandboxDeployment:
    """Manage the storage stack, sandbox image, and runtime stack in one AWS account."""

    def __init__(self) -> None:
        session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        self.profile = session.profile_name or "default credential chain"
        self.region = session.region_name or "us-east-1"
        self.partition = session.get_partition_for_region(self.region)
        self.account = session.client("sts", region_name=self.region).get_caller_identity()["Account"]
        self.bucket = BUCKET_NAME or f"{DEPLOYMENT_NAME}-{self.account}-{self.region}"
        validate_bucket(self.bucket)
        self.cloudformation = session.client("cloudformation", region_name=self.region)
        self.ecr = session.client("ecr", region_name=self.region)
        self.agentcore = session.client("bedrock-agentcore-control", region_name=self.region)
        self.logs = session.client("logs", region_name=self.region)
        self.xray = session.client("xray", region_name=self.region)
        self.foundation_stack = f"{DEPLOYMENT_NAME}-foundation"
        self.runtime_stack = f"{DEPLOYMENT_NAME}-runtime"
        self.foundation_parameters = {
            "BucketName": self.bucket,
            "RepositoryName": DEPLOYMENT_NAME,
            "RuntimeName": runtime_name(),
        }
        self.runtime_parameters = {
            "BucketName": self.bucket,
            "CheckpointPrefix": CHECKPOINT_PREFIX,
            "RuntimeName": runtime_name(),
        }

    def get_stack(self, name: str) -> dict[str, Any] | None:
        try:
            stack = self.cloudformation.describe_stacks(StackName=name)["Stacks"][0]
        except ClientError as error:
            details = error.response["Error"]
            if details["Code"] == "ValidationError" and "does not exist" in details["Message"]:
                return None
            raise
        tags = {tag["Key"]: tag["Value"] for tag in stack.get("Tags", [])}
        if tags.get("ManagedBy") != OWNER:
            raise RuntimeError(f"Refusing to change unrelated stack {name}.")
        return stack

    def check_stack(self, name: str, parameters: dict[str, str]) -> dict[str, Any] | None:
        stack = self.get_stack(name)
        if stack is None:
            return None
        if stack["StackStatus"] not in {"CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"}:
            raise RuntimeError(f"{name} is {stack['StackStatus']}. Inspect its CloudFormation events before retrying.")
        existing = {item["ParameterKey"]: item["ParameterValue"] for item in stack.get("Parameters", [])}
        for key in ("BucketName", "RepositoryName", "RuntimeName", "CheckpointPrefix"):
            if key in existing and key in parameters and parameters[key] != existing[key]:
                raise RuntimeError(f"Changing {key} needs a migration. Use a new DEPLOYMENT_NAME for a separate setup.")
        return stack

    def check_existing_stacks(self) -> None:
        self.check_stack(self.foundation_stack, self.foundation_parameters)
        self.check_stack(self.runtime_stack, self.runtime_parameters)

    def deploy_stack(self, name: str, template: str, parameters: dict[str, str]) -> dict[str, str]:
        existing = self.check_stack(name, parameters)
        request = {
            "StackName": name,
            "TemplateBody": template,
            "Parameters": [{"ParameterKey": key, "ParameterValue": value} for key, value in parameters.items()],
            "Capabilities": ["CAPABILITY_IAM"],
            "Tags": [{"Key": "ManagedBy", "Value": OWNER}],
        }
        if existing:
            try:
                self.cloudformation.update_stack(**request)
            except ClientError as error:
                details = error.response["Error"]
                if details["Code"] == "ValidationError" and "No updates are to be performed" in details["Message"]:
                    console.print(f"[dim]{name} is already up to date.[/dim]")
                    return stack_outputs(existing)
                raise
            waiter = self.cloudformation.get_waiter("stack_update_complete")
        else:
            self.cloudformation.create_stack(**request)
            waiter = self.cloudformation.get_waiter("stack_create_complete")
        with console.status(f"Waiting for {name}…"):
            try:
                waiter.wait(StackName=name, WaiterConfig={"Delay": 5, "MaxAttempts": 240})
            except WaiterError as error:
                raise RuntimeError(
                    f"{name} did not complete. Inspect its CloudFormation events before retrying."
                ) from error
        return stack_outputs(self.get_stack(name))

    def publish_image(self, repository: str) -> str:
        token = self.ecr.get_authorization_token()["authorizationData"][0]["authorizationToken"]
        username, password = base64.b64decode(token).decode().split(":", 1)
        run_docker(
            "login", "--username", username, "--password-stdin", repository.split("/")[0], stdin=password, quiet=True
        )
        image = f"{repository}:build-{uuid4().hex[:12]}"
        run_docker("build", "--platform", "linux/arm64", "--load", "--target", "sandbox", "--tag", image, str(ROOT))
        run_docker("push", image)
        return image

    def runtime_states(self, runtime_id: str) -> dict[str, str]:
        runtime = self.agentcore.get_agent_runtime(agentRuntimeId=runtime_id)
        try:
            endpoint = self.agentcore.get_agent_runtime_endpoint(agentRuntimeId=runtime_id, endpointName="DEFAULT")
            endpoint_status = endpoint["status"]
        except ClientError as error:
            if error.response["Error"]["Code"] != "ResourceNotFoundException":
                raise
            endpoint_status = "NOT_CREATED"
        return {"RuntimeStatus": runtime["status"], "EndpointStatus": endpoint_status}

    def wait_for_runtime(self, runtime_id: str) -> None:
        deadline = time.monotonic() + 1200
        with console.status("Waiting for the AgentCore runtime…") as progress:
            while time.monotonic() < deadline:
                states = self.runtime_states(runtime_id)
                if all(state == "READY" for state in states.values()):
                    return
                if any("FAILED" in state or state.startswith("DELET") for state in states.values()):
                    raise RuntimeError(f"AgentCore did not become ready: {states}. Inspect the runtime in AWS.")
                progress.update(f"Runtime: {states['RuntimeStatus']} · Endpoint: {states['EndpointStatus']}")
                time.sleep(10)
        raise RuntimeError("Timed out waiting for AgentCore. Resources remain available for inspection.")

    def runtime_tracing(self, runtime_arn: str | None) -> str:
        """Inspect trace delivery configuration without claiming telemetry has arrived."""
        if not runtime_arn:
            return "NOT_CONFIGURED"
        sources = self.logs.get_paginator("describe_delivery_sources")
        found_source = False
        for page in sources.paginate(resourceArns=[runtime_arn]):
            for source in page.get("deliverySources", []):
                if source["logType"] != "TRACES" or runtime_arn not in source["resourceArns"]:
                    continue
                found_source = True
                if source.get("status") == "INACTIVE":
                    continue
                deliveries = self.logs.get_paginator("describe_deliveries")
                for delivery_page in deliveries.paginate(deliverySourceNames=[source["name"]]):
                    if any(
                        item["deliveryDestinationType"] == "XRAY" and item["deliverySourceName"] == source["name"]
                        for item in delivery_page.get("deliveries", [])
                    ):
                        return "CONFIGURED"
        return "INCOMPLETE" if found_source else "NOT_CONFIGURED"

    def observability_status(self, runtime_arn: str | None) -> dict[str, str]:
        destination = self.xray.get_trace_segment_destination()
        state = destination["Status"] if destination["Destination"] == "CloudWatchLogs" else "NOT_ENABLED"
        return {
            "TransactionSearch": state,
            "RuntimeTraceDelivery": self.runtime_tracing(runtime_arn),
            "CloudWatch": f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}",
        }

    def enable_transaction_search(self) -> None:
        """Enable the shared destination without changing existing sampling or policies."""
        destination = self.xray.get_trace_segment_destination()
        if destination["Destination"] != "CloudWatchLogs":
            if destination["Status"] == "PENDING":
                raise RuntimeError("The X-Ray destination is changing. Wait for it to settle, then run apply again.")
            policy_name = "agno-agentcore-transaction-search"
            arn = f"arn:{self.partition}"
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "TransactionSearchXRayAccess",
                        "Effect": "Allow",
                        "Principal": {"Service": "xray.amazonaws.com"},
                        "Action": "logs:PutLogEvents",
                        "Resource": [
                            f"{arn}:logs:{self.region}:{self.account}:log-group:aws/spans:*",
                            f"{arn}:logs:{self.region}:{self.account}:log-group:/aws/application-signals/data:*",
                        ],
                        "Condition": {
                            "ArnLike": {"aws:SourceArn": f"{arn}:xray:{self.region}:{self.account}:*"},
                            "StringEquals": {"aws:SourceAccount": self.account},
                        },
                    }
                ],
            }
            existing = None
            for page in self.logs.get_paginator("describe_resource_policies").paginate():
                for item in page.get("resourcePolicies", []):
                    if item["policyName"] == policy_name:
                        existing = json.loads(item["policyDocument"])
            if existing is not None and existing != policy:
                raise RuntimeError(f"{policy_name} already has different permissions. Review it before retrying.")
            if existing is None:
                self.logs.put_resource_policy(policyName=policy_name, policyDocument=json.dumps(policy))
            self.xray.update_trace_segment_destination(Destination="CloudWatchLogs")

        deadline = time.monotonic() + 600
        with console.status("Waiting for CloudWatch Transaction Search…"):
            while time.monotonic() < deadline:
                destination = self.xray.get_trace_segment_destination()
                if destination["Destination"] == "CloudWatchLogs" and destination["Status"] == "ACTIVE":
                    return
                time.sleep(5)
        raise RuntimeError("Transaction Search is still pending. Wait, then run apply again; settings are retained.")

    def manage_trace_delivery(self) -> str:
        """Keep stack-owned tracing managed; reuse an existing external delivery."""
        runtime = stack_outputs(self.get_stack(self.runtime_stack))
        if "TraceDeliveryArn" in runtime:
            return "true"
        state = self.runtime_tracing(runtime.get("RuntimeArn"))
        if state == "INCOMPLETE":
            raise RuntimeError(
                "Existing runtime tracing is incomplete. Repair its CloudWatch delivery before applying."
            )
        return "false" if state == "CONFIGURED" else "true"

    def provision(self) -> dict[str, str]:
        manage_traces = self.manage_trace_delivery()
        console.rule("Enable runtime observability")
        self.enable_transaction_search()
        console.rule("1 · Create image and checkpoint storage")
        foundation = self.deploy_stack(self.foundation_stack, FOUNDATION_TEMPLATE, self.foundation_parameters)
        console.rule("2 · Build and publish the sandbox image")
        image = self.publish_image(foundation["RepositoryUri"])
        console.rule("3 · Create or update the AgentCore runtime")
        runtime = self.deploy_stack(
            self.runtime_stack,
            RUNTIME_TEMPLATE,
            {
                **self.runtime_parameters,
                "ImageUri": image,
                "ExecutionRoleArn": foundation["ExecutionRoleArn"],
                "CreateTraceDelivery": manage_traces,
            },
        )
        self.wait_for_runtime(runtime["RuntimeId"])
        runtime.update(self.observability_status(runtime["RuntimeArn"]))
        console.print("[green]Sandbox resources are ready.[/green]")
        return runtime

    def inspect(self) -> dict[str, str]:
        foundation = self.get_stack(self.foundation_stack)
        runtime = self.get_stack(self.runtime_stack)
        result = {
            **stack_outputs(foundation),
            **stack_outputs(runtime),
            "FoundationStackStatus": foundation["StackStatus"] if foundation else "NOT_CREATED",
            "RuntimeStackStatus": runtime["StackStatus"] if runtime else "NOT_CREATED",
        }
        if "RuntimeId" in result:
            result.update(self.runtime_states(result["RuntimeId"]))
        result.update(self.observability_status(result.get("RuntimeArn")))
        return result


def stack_outputs(stack: dict[str, Any] | None) -> dict[str, str]:
    return {item["OutputKey"]: item["OutputValue"] for item in (stack or {}).get("Outputs", [])}


def run_docker(*args: str, stdin: str | None = None, quiet: bool = False) -> None:
    """Leave build progress visible; send the ECR password only over stdin."""
    result = subprocess.run(["docker", *args], input=stdin, text=True, capture_output=quiet, check=False)
    if result.returncode:
        raise RuntimeError(f"Docker {args[0]} failed (exit {result.returncode}). Check Docker and retry.")


def show_table(title: str, values: dict[str, str]) -> None:
    table = Table(title=title, show_header=False, title_style="bold cyan")
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    for label, value in values.items():
        table.add_row(Text(label), Text(value))
    console.print(table)


def show_connection(values: dict[str, str], region: str) -> None:
    show_table("AWS sandbox", values)
    console.print(
        "[dim]Trace delivery status describes configuration, not received data. "
        "Run a sandbox session, then inspect AgentCore Observability or CloudWatch; "
        "new traces can take about 10 minutes to appear.[/dim]"
    )
    if not all(key in values for key in ("RuntimeArn", "CheckpointBucket", "CheckpointPrefix", "ApplicationUser")):
        console.print(
            "[yellow]Setup is incomplete. Run apply for a new setup, or inspect CloudFormation events.[/yellow]"
        )
        return
    console.print("\n[bold]Configure app/sandbox.py[/bold]")
    console.print("Set SANDBOX_ENABLED = True and REPOSITORY to your GitHub URL and branch.")
    console.print("\n[bold]Set these in your API host's environment settings[/bold]")
    environment = {
        "SANDBOX_PROVIDER": "agentcore",
        "AWS_REGION": region,
        "AGENTCORE_RUNTIME_ARN": values["RuntimeArn"],
        "AGENTCORE_CHECKPOINT_BUCKET": values["CheckpointBucket"],
        "AGENTCORE_CHECKPOINT_PREFIX": values["CheckpointPrefix"],
    }
    show_code("\n".join(f"{key}={value}" for key, value in environment.items()), "bash")
    console.print(
        "Create an access key for ApplicationUser in IAM and enter it directly in your host's secret settings."
    )
    console.print("[dim]Follow docs/harnesses.md to deploy the API, test checkpoint recovery, and clean up.[/dim]")


def show_code(code: str, language: str) -> None:
    # Preserve long ARNs when copying output from a narrow terminal.
    width = max(len(line) for line in code.splitlines())
    console.print(Syntax(code, language, code_width=width, word_wrap=False), soft_wrap=True)


@contextmanager
def report_errors() -> Iterator[None]:
    try:
        yield
    except (BotoCoreError, ClientError, OSError, RuntimeError, ValueError) as error:
        console.print(Text(str(error), style="bold red"))
        raise typer.Exit(code=1) from None


# CloudFormation owns deployment resources; Transaction Search is shared account state.
FOUNDATION_TEMPLATE = """\
AWSTemplateFormatVersion: '2010-09-09'
Description: Image storage, checkpoint storage and execution role for an Agno sandbox.
Parameters:
  BucketName:
    Type: String
  RepositoryName:
    Type: String
  RuntimeName:
    Type: String
Resources:
  Checkpoints:
    Type: AWS::S3::Bucket
    DeletionPolicy: Retain
    UpdateReplacePolicy: Retain
    Properties:
      BucketName: !Ref BucketName
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        IgnorePublicAcls: true
        BlockPublicPolicy: true
        RestrictPublicBuckets: true
      OwnershipControls:
        Rules:
          - ObjectOwnership: BucketOwnerEnforced
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      LifecycleConfiguration:
        Rules:
          - Id: AbortIncompleteUploads
            Status: Enabled
            AbortIncompleteMultipartUpload:
              DaysAfterInitiation: 7
  CheckpointPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref Checkpoints
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Deny
            Principal: '*'
            Action: 's3:*'
            Resource:
              - !GetAtt Checkpoints.Arn
              - !Sub '${Checkpoints.Arn}/*'
            Condition:
              Bool:
                aws:SecureTransport: 'false'
  Images:
    Type: AWS::ECR::Repository
    DeletionPolicy: Retain
    UpdateReplacePolicy: Retain
    Properties:
      RepositoryName: !Ref RepositoryName
      ImageTagMutability: IMMUTABLE
      EncryptionConfiguration:
        EncryptionType: AES256
      ImageScanningConfiguration:
        ScanOnPush: true
  ExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: bedrock-agentcore.amazonaws.com
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                aws:SourceAccount: !Ref AWS::AccountId
              ArnLike:
                aws:SourceArn: !Sub 'arn:${AWS::Partition}:bedrock-agentcore:${AWS::Region}:${AWS::AccountId}:*'
      Policies:
        - PolicyName: PullImageAndWriteLogs
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action: [ecr:BatchGetImage, ecr:GetDownloadUrlForLayer]
                Resource: !GetAtt Images.Arn
              - Effect: Allow
                Action: ecr:GetAuthorizationToken
                Resource: '*'
              - Effect: Allow
                Action: [logs:CreateLogGroup, logs:DescribeLogStreams]
                Resource: !Sub
                  - 'arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:${LogName}'
                  - LogName: !Sub '/aws/bedrock-agentcore/runtimes/${RuntimeName}-*'
              - Effect: Allow
                Action: [logs:CreateLogStream, logs:PutLogEvents]
                Resource: !Sub
                  - 'arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:${LogName}:log-stream:*'
                  - LogName: !Sub '/aws/bedrock-agentcore/runtimes/${RuntimeName}-*'
Outputs:
  BucketName:
    Value: !Ref Checkpoints
  RepositoryUri:
    Value: !GetAtt Images.RepositoryUri
  ExecutionRoleArn:
    Value: !GetAtt ExecutionRole.Arn
"""

RUNTIME_TEMPLATE = """\
AWSTemplateFormatVersion: '2010-09-09'
Description: Agno sandbox runtime and a restricted identity for its API caller.
Parameters:
  RuntimeName:
    Type: String
  ImageUri:
    Type: String
  ExecutionRoleArn:
    Type: String
  BucketName:
    Type: String
  CheckpointPrefix:
    Type: String
  CreateTraceDelivery:
    Type: String
    Default: 'true'
    AllowedValues: ['true', 'false']
Conditions:
  ManageTraceDelivery: !Equals [!Ref CreateTraceDelivery, 'true']
Resources:
  Runtime:
    Type: AWS::BedrockAgentCore::Runtime
    Properties:
      AgentRuntimeName: !Ref RuntimeName
      AgentRuntimeArtifact:
        ContainerConfiguration:
          ContainerUri: !Ref ImageUri
      RoleArn: !Ref ExecutionRoleArn
      NetworkConfiguration:
        NetworkMode: PUBLIC
      ProtocolConfiguration: HTTP
      LifecycleConfiguration:
        IdleRuntimeSessionTimeout: 900
        MaxLifetime: 3600
  RuntimeTraceSource:
    Type: AWS::Logs::DeliverySource
    Condition: ManageTraceDelivery
    Properties:
      Name: !Sub '${RuntimeName}-traces'
      LogType: TRACES
      ResourceArn: !GetAtt Runtime.AgentRuntimeArn
  RuntimeTraceDestination:
    Type: AWS::Logs::DeliveryDestination
    Condition: ManageTraceDelivery
    Properties:
      Name: !Sub '${RuntimeName}-xray'
      DeliveryDestinationType: XRAY
  RuntimeTraceDelivery:
    Type: AWS::Logs::Delivery
    Condition: ManageTraceDelivery
    DependsOn: RuntimeTraceSource
    Properties:
      DeliverySourceName: !Sub '${RuntimeName}-traces'
      DeliveryDestinationArn: !GetAtt RuntimeTraceDestination.Arn
  ApplicationCaller:
    Type: AWS::IAM::User
    Properties:
      Policies:
        - PolicyName: UseSandboxAndCheckpoints
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - bedrock-agentcore:InvokeAgentRuntime
                  - bedrock-agentcore:InvokeAgentRuntimeCommand
                  - bedrock-agentcore:StopRuntimeSession
                Resource:
                  - !GetAtt Runtime.AgentRuntimeArn
                  - !Sub '${Runtime.AgentRuntimeArn}/runtime-endpoint/DEFAULT'
              - Effect: Allow
                Action: [s3:GetObject, s3:PutObject, s3:DeleteObject, s3:AbortMultipartUpload]
                Resource: !Sub 'arn:${AWS::Partition}:s3:::${BucketName}/${CheckpointPrefix}*'
              - Effect: Allow
                Action: s3:ListBucket
                Resource: !Sub 'arn:${AWS::Partition}:s3:::${BucketName}'
Outputs:
  TraceDeliveryArn:
    Condition: ManageTraceDelivery
    Value: !GetAtt RuntimeTraceDelivery.Arn
  RuntimeArn:
    Value: !GetAtt Runtime.AgentRuntimeArn
  RuntimeId:
    Value: !GetAtt Runtime.AgentRuntimeId
  ApplicationUser:
    Value: !Ref ApplicationCaller
  CheckpointBucket:
    Value: !Ref BucketName
  CheckpointPrefix:
    Value: !Ref CheckpointPrefix
  AwsRegion:
    Value: !Ref AWS::Region
"""


if __name__ == "__main__":
    app()
