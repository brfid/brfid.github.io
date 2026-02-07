terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data source for latest Ubuntu 22.04 AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security group for SSH access
resource "aws_security_group" "arpanet_test" {
  name        = "arpanet-test-sg"
  description = "Security group for ARPANET testing instance"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "arpanet-test"
    Project = "brfid.github.io"
    Purpose = "ARPANET debugging"
  }
}

# SSH key pair
resource "aws_key_pair" "arpanet_test" {
  key_name   = "arpanet-test-key"
  public_key = file(var.ssh_public_key_path)

  tags = {
    Name    = "arpanet-test"
    Project = "brfid.github.io"
  }
}

# EC2 instance
resource "aws_instance" "arpanet_test" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = aws_key_pair.arpanet_test.key_name

  vpc_security_group_ids = [aws_security_group.arpanet_test.id]

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true
  }

  user_data = templatefile("${path.module}/user-data.sh", {
    git_repo   = var.git_repo
    git_branch = var.git_branch
  })

  tags = {
    Name    = "arpanet-test"
    Project = "brfid.github.io"
    Purpose = "ARPANET debugging"
  }

  # Wait for instance to be ready
  provisioner "remote-exec" {
    inline = [
      "cloud-init status --wait"
    ]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = self.public_ip
      private_key = file(var.ssh_private_key_path)
      timeout     = "10m"
    }
  }
}
