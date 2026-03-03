locals {
  common_tags = merge(
    {
      project     = "governance-starter"
      environment = terraform.workspace
      managed_by  = "terraform"
    },
    var.tags,
  )
}
