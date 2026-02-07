variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 30
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key"
  type        = string
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed to SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "git_repo" {
  description = "Git repository URL"
  type        = string
  default     = "https://github.com/brfid/brfid.github.io.git"
}

variable "git_branch" {
  description = "Git branch to checkout"
  type        = string
  default     = "claude/arpanet-build-integration-uU9ZL"
}
