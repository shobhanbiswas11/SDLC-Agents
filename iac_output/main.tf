provider "aws" {
  region = "ap-south-1"
}

resource "aws_instance" "example" {
  ami           = "ami-0c1a7f89451184c8b" # Replace with the latest Amazon Linux 2 AMI ID for ap-south-1
  instance_type = "t2.micro"
  security_groups = [aws_security_group.example_sg.name]

  tags = {
    Name        = "example-instance"
    Environment = "dev"
    Owner       = "team@example.com"
    Project     = "example-project"
    CostCenter  = "12345"
  }

  root_block_device {
    encrypted = true
  }
}

resource "aws_security_group" "example_sg" {
  name        = "example-sg"
  description = "Security group for example instance"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"] # Restrict SSH access to a private network
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"] # Restrict outbound traffic to necessary IP ranges and ports
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"] # Restrict outbound traffic to necessary IP ranges and ports
  }

  tags = {
    Name        = "example-sg"
    Environment = "dev"
    Owner       = "team@example.com"
    Project     = "example-project"
    CostCenter  = "12345"
  }
}