# declare necessary variables

variable "EC2_INSTANCE_TAG_NAME" {
  default     = "Backup"
  description = "Name of the tag that identifies target EC2 instances to snapshot."
}

variable "EC2_INSTANCE_TAG_VALUE" {
  default     = "true"
  description = "Name of the value of the tag that identifies target EC2 instances to snapshot"
}

variable "RETENTION_DAYS" {
  default = 5
  description = "Numbers of distinct days that the EBS Snapshots will be stored (integer)"
}

variable "VOLUME_TAG_NAMES_TO_RETAIN" {
  default = []
  type = "list"
  description = "List of volume tag names, which will be copied to the snapshot tags from the volume"
}

variable "unique_name" {
  default = "v1"
  description = "Enter Unique Name to identify the Terraform Stack (lowercase)"
}

variable "stack_prefix" {
  default = "ebs_bckup"
  description = "Stack Prefix for resource generation"
}

variable "cron_expression" {
  description = "Cron expression for firing up the Lambda Function, required"
}

variable "regions" {
  type = "list"
  description = "List of regions in which this Lambda function may run. At least one region is required."
}

variable "timeout" {
  default = "60"
  description = "Number of seconds that the snapshotting Lambda is allowed to run. Increase if you have a large number of instances."
}
