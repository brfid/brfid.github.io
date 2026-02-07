output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.arpanet_test.id
}

output "instance_public_ip" {
  description = "Public IP address"
  value       = aws_instance.arpanet_test.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name"
  value       = aws_instance.arpanet_test.public_dns
}

output "ssh_command" {
  description = "SSH connection command"
  value       = "ssh -i ${var.ssh_private_key_path} ubuntu@${aws_instance.arpanet_test.public_ip}"
}
