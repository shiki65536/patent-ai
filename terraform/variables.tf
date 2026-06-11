variable "aws_region" {
  default = "ap-southeast-2"
}

variable "aws_account_id" {
  default = "446143278521"
}

variable "api_secret" {
  sensitive = true
}

variable "google_api_key" {
  sensitive = true
}

variable "anthropic_api_key" {
  sensitive = true
}
