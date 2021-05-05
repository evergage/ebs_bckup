# ebs\_bckup
## A Lambda-Powered EBS Snapshot Terraform Module

A Terraform module for creating a Lambda Function that takes automatic snapshots of of all connected EBS volumes of correspondingly tagged instances.
The function is triggered via a CloudWatch event that can be freely configured by a cron expression.

## Input Variables

Refer to [variables.tf](variables.tf) for all inputs with descriptions and defaults. 

## Outputs
Default outputs are `aws_iam_role_arn` with the value of the created IAM role for the Lambda function and the `lambda_function_name`

## Retention Policy

RETENTION_DAYS setting is a *count of unique days*, not merely a time-based cut-off relative to now. As a result,
if this module is disabled for a day, but is enabled the next day, it will only remove the one oldest day of snapshots,
not two days.


## Example usage
In your Terrafom `main.tf` call the module with the required variables.

```
module "ebs_bckup" {
  // It is recommended that you lock "ref" to a specific release version
  source = "git::https://github.com/evergage/ebs_bckup.git?ref=v1.3"
  EC2_INSTANCE_TAG_NAME      = "environment"
  EC2_INSTANCE_TAG_VALUE     = "prod"
  RETENTION_DAYS             = 10
  VOLUME_TAG_NAMES_TO_RETAIN = [
    "environment",
    "Kind"
  ]
  unique_name      = "v2"
  stack_prefix     = "ebs_snapshot"
  cron_expression  = "45 1 * * ? *"
  regions          = ["eu-west-1", "eu-central-1"]
  timeout          = 120
}
```

# Release Instructions

You must add a release "v1.#" tag pointing at the latest changes, if the changes are complete and releasable.
