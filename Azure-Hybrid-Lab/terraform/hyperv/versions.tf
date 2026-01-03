# =============================================================================
# Terraform Configuration - Hyper-V Provider
# =============================================================================
# Uses the taliesins/hyperv community provider to manage Hyper-V VMs
# Requires running Terraform on Windows with Hyper-V role installed
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    hyperv = {
      source  = "taliesins/hyperv"
      version = "~> 1.2.0"
    }
  }
}

# Configure the Hyper-V Provider
# Runs locally on the Hyper-V host
provider "hyperv" {
  # Using WinRM for local management
  # No explicit configuration needed when running locally on Hyper-V host
}
