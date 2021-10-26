# EBS-Pricing

## Goal
The goal of this project is to create an up-to-date source for AWS EBS Pricing data that can be used programmatically. The context is to support tools that can look at EBS volumes information in an account (e.g., region, availability zone, type, size, etc.) and determine what their monthly costs would be.

## Quick Summary/Usage
GitHub Pages hosted summary (as well as an example) can be found [here](https://cloudkeep-io.github.io/ebs-pricing).

To just download the up to ebs pricing data json:
```
curl https://cloudkeep-io.github.io/ebs-pricing/ebs_pricing.json
```

## Challenge and Work-around
Official AWS resources for calcualting costs for using EBS volumes can be found [here](https://aws.amazon.com/ebs/pricing/). There is also a calculator linked there where you can enter in the region and EBS volume info, and it will provide your monthly cost. 

The official programmatic way of retrieving the pricing information is via the [AWS Price List API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html). These entries are basically prices categorized by various fields, so we can determine, e.g., what is the price of EBS gp2 volume per Gib-month in us-east-1? 

However, the region code (e.g., "us-east-1") is not one of the fields in the price records. Instead something called "location" is given (e.g., "US East (N. Virginia)").

There is (as far as we can tell) no API that map the region/zone codes to the location descriptions. What we see is that the [SSM API](https://aws.amazon.com/blogs/aws/new-query-for-aws-regions-endpoints-and-more-using-aws-systems-manager-parameter-store/) can map region/zone codes to `location`s but only for Local Zones and Wavelength Zones(*).  For Regions, the closest we can find is the `longName` attribute which matches the `location` descriptions for all the regions except those in Europe. For the regions in Europe, the "longName" take on the form "Europe (Frankfort)" whereas the "location" is "EU (Frankfort)". Thus we will here "calculate" the `location` of a region by simply substituting "Europe" in `longName` with "EU". Perhaps one day, the SSM database will be updated to include the `location` fields at which point we can drop this work-around. (Or better yet, the pricing API can include the region/zone codes.)

It is also of note that not all of these region/zone codes map uniquely to a location. Two Local Zones (us-west-2-lax-1a us-west-2-lax-1b) map to the location of "US West (Los Angeles)"

(*) Actually, the `location` for one of the Wavelength Zones ("US East (Verizon) – Washington DC") uses an em-dash, instead of a hyphen, in the SSM record. This also needed to be corrected.


## Automatic Update
Currently we use GitHub Actions to run the Makefile to update the pricing information each day at 0500 UTC. Note the code accounts for scenarios like new regions, but not new volume types. If the build fails (as can happen when a new volume type is introduced) the maintainers are notified so that we can make appropriate corrections.

## Details

### Pricing API
All the prices for EBS volumes can be gotten via the AWS Price List API, filtered on serviceCode="AmazonEC2" and productFamily="Storage" | "System Operation" | "Provisioned Throughput". You can use the following CLI commands to save these in a file, `prices.json`:
```
aws pricing get-products --service-code "AmazonEC2" --filter Type=TERM_MATCH,Field=ProductFamily,Value=Storage --output json | jq -r '.PriceList[]' > prices.json
aws pricing get-products --service-code "AmazonEC2" --filter Type=TERM_MATCH,Field=ProductFamily,Value="System Operation" --output json | jq -r '.PriceList[]' >> prices.json
aws pricing get-products --service-code "AmazonEC2" --filter Type=TERM_MATCH,Field=ProductFamily,Value="Provisioned Throughput" --output json | jq -r '.PriceList[]' >> prices.json
```

The relevant fields in the pricing records are:
* .product.attributes.location: location of the EBS volume
* .product.attributes.volumeApiName : Volume Type (e.g., "gp2")
* .product.productFamily : Cost Type - "Storage" for cost associated with how much storage is provisioned, "System Operation" for cost associated with how much IOPS, and "Provisioned Throughput" for cost associated with how much throughput is provisioned.
* .product.attributes.group : IOPS Tier Type - for Volume Type "io2", we have different price for different tier of IOPS allocated.
* .terms.OnDemand[].priceDimensions[].pricePerUnit - contains the currency and the value of the price per unit
* .terms.OnDemand[].priceDimensions[].unit - contains the unit of service priced (e.g., "GB-mo")

The following jq command can surface these values
```
cat prices.json | jq '.product.attributes.location + "-" + .product.attributes.volumeApiName + "-" + .product.productFamily + "-" + .product.attributes.group + "-" + ": " + (.terms.OnDemand[].priceDimensions[].pricePerUnit | keys[]) + " " + (.terms.OnDemand[].priceDimensions[].pricePerUnit[]) + "/" + .terms.OnDemand[].priceDimensions[].unit' | sort 
```

### SSM API
There are three different types of `location`s that EBS volumes can be deployed to currently: Regions, Local Zones, and Wavelength Zones. They are enumerated via SSM at these paths:
```
aws ssm get-parameters-by-path --path /aws/service/global-infrastructure/regions --output json
aws ssm get-parameters-by-path --path /aws/service/global-infrastructure/local-zones --output json
aws ssm get-parameters-by-path --path /aws/service/global-infrastructure/wavelength-zones --output json
```

For Local Zones and Wavelength Zones, the location string can be gotten in this manner:
```
$ aws ssm get-parameter --name /aws/service/global-infrastructure/wavelength-zones/apne1-wl1-kix-wlz1/location --output json | jq '.Parameter.Value'
"Asia Pacific (KDDI) - Osaka"
```

As mentioned above, there is no `location` parameter for a Region. However, we can get the `longName` which is close:
```
$ aws ssm get-parameter  --name /aws/service/global-infrastructure/regions/eu-central-1/longName --output json | jq '.'  | jq '.Parameter.Value'
"Europe (Frankfurt)"
```
Note if there is a `/aws/service/global-infrastructure/regions/eu-central-1/location`, it would have been `"EU (Frankfurt)"`.

### get_ebs_pricing.py
We have put together a simple boto3 python script to combine the above observations to create ebs_pricing.json. It calls the SSM API to create a region/zone code to location mapping, calls the Pricing API to get the list of EBS related prices, and combines the two. Note it uses poetry. To execute:
```
poetry install
poetry run python get_ebs_pricing.py
```

