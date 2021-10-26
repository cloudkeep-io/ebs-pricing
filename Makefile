NOW:=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

.PHONY: update
update: 
	poetry run python get_ebs_pricing.py > docs/ebs_pricing.json
	echo $(NOW) > docs/last_checked

prices.json:
	aws pricing get-products --service-code "AmazonEC2" --filter Type=TERM_MATCH,Field=ProductFamily,Value=Storage --output json | jq -r '.PriceList[]' > prices.json
	aws pricing get-products --service-code "AmazonEC2" --filter Type=TERM_MATCH,Field=ProductFamily,Value="System Operation" --output json | jq -r '.PriceList[]' >> prices.json
	aws pricing get-products --service-code "AmazonEC2" --filter Type=TERM_MATCH,Field=ProductFamily,Value="Provisioned Throughput" --output json | jq -r '.PriceList[]' >> prices.json

.PHONY: show-prices
show-prices: prices.json
	cat prices.json | jq '.product.attributes.location + "-" + .product.attributes.volumeApiName + "-" + .product.productFamily + "-" + .product.attributes.group + "-" + ": " + (.terms.OnDemand[].priceDimensions[].pricePerUnit | keys[]) + " " + (.terms.OnDemand[].priceDimensions[].pricePerUnit[]) + "/" + .terms.OnDemand[].priceDimensions[].unit' | sort

ssm-gi.json:
	aws ssm get-parameters-by-path --recursive  --path /aws/service/global-infrastructure  --output json > ssm-gi.json

.PHONY: list-rzs
list-rzs:
	aws ssm get-parameters-by-path --path /aws/service/global-infrastructure/regions --output json
	aws ssm get-parameters-by-path --path /aws/service/global-infrastructure/local-zones --output json
	aws ssm get-parameters-by-path --path /aws/service/global-infrastructure/wavelength-zones --output json

.PHONY: clean
clean:
	rm -rf ssm-gi.json prices.json
