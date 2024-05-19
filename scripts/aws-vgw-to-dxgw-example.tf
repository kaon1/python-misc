### Example Terraform File to Create VGW Resources and Peer to a Direct Connect Gateway in another AWS Account

# Autonomous System Numbers (ASNs) to use for East and West VGWs to peer to Direct Connect Gateway (dxgw)
variable "vgw-asn-east" {
  type        = string
  description = "ASN to use for this account - EAST"
  # CHANGE THIS PER ACCOUNT AND VPC
  default = "xxxx"
}
variable "vgw-asn-west" {
  type        = string
  description = "ASN to use for this account - WEST"
  # CHANGE THIS PER ACCOUNT AND VPC
  default = "xxxx"
}

# DXGW ID For New Gateway (for partner)
variable "dxgw-id-partner" {
  type        = string
  description = "DXGW ID"
  default     = "xxx"
}

# Create East VGW with custom ASN 
resource "aws_vpn_gateway" "vgw-east-to-dxgw-partner" {
  provider        = aws.us-east-1
  vpc_id          = module.vpc-east.vpc_id
  amazon_side_asn = var.vgw-asn-east

  tags = {
    Name = "${var.account_name}-east-to-dxgw-partner"
  }
}

# Create West VGW with custom ASN 
resource "aws_vpn_gateway" "vgw-west-to-dxgw-partner" {
  provider        = aws.us-west-2
  vpc_id          = module.vpc-west.vpc_id
  amazon_side_asn = var.vgw-asn-west

  tags = {
    Name = "${var.account_name}-west-to-dxgw-partner"
  }
}

# Attach East VGW to East VPC
resource "aws_vpn_gateway_attachment" "vpn_attachment_east" {
  provider       = aws.us-east-1
  vpc_id         = module.vpc-east.vpc_id
  vpn_gateway_id = aws_vpn_gateway.vgw-east-to-dxgw-partner.id
}
# Attach West VGW to West VPC
resource "aws_vpn_gateway_attachment" "vpn_attachment_west" {
  provider       = aws.us-west-2
  vpc_id         = module.vpc-west.vpc_id
  vpn_gateway_id = aws_vpn_gateway.vgw-west-to-dxgw-partner.id
}

# Enable Route Propogation to East Private Route Tables A/B/C
resource "aws_vpn_gateway_route_propagation" "route-props-vgw-east" {
  provider       = aws.us-east-1
  count          = length(module.vpc-east.private_route_table_ids)
  route_table_id = module.vpc-east.private_route_table_ids[count.index]
  vpn_gateway_id = aws_vpn_gateway.vgw-east-to-dxgw-partner.id
}

# Enable Route Propogation to West Private Route Tables A/B/C
resource "aws_vpn_gateway_route_propagation" "route-props-vgw-west" {
  provider       = aws.us-west-2
  count          = length(module.vpc-west.private_route_table_ids)
  route_table_id = module.vpc-west.private_route_table_ids[count.index]
  vpn_gateway_id = aws_vpn_gateway.vgw-west-to-dxgw-partner.id
}

# Propose VGW to DXGW Association to hub account - EAST
resource "aws_dx_gateway_association_proposal" "vgw-to-dxgw-association-east" {
  provider                    = aws.us-east-1
  dx_gateway_id               = var.dxgw-id-partner
  dx_gateway_owner_account_id = var.network_accountid
  associated_gateway_id       = aws_vpn_gateway.vgw-east-to-dxgw-partner.id
  allowed_prefixes            = [local.vpc_east_cidr]
}

# Propose VGW to DXGW Association to hub account - WEST
resource "aws_dx_gateway_association_proposal" "vgw-to-dxgw-association-west" {
  provider                    = aws.us-west-2
  dx_gateway_id               = var.dxgw-id-partner
  dx_gateway_owner_account_id = var.network_accountid
  associated_gateway_id       = aws_vpn_gateway.vgw-west-to-dxgw-partner.id
  allowed_prefixes            = [local.vpc_west_cidr]
}
