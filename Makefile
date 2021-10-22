# 
# "Raw" data is pulled from AWS API to price_spool_raw/
# "Core" (or cooked) data then created and put to price_spool/
# if core data is "new" (check the result of jsondiff), then do 'update':
#  - copy the latest price_spool_raw data to price_db_raw, and 
#  - copy the latest price_spool data to price_db
#

NOW:=$(shell date -u +"%Y-%m-%dZ%H-%M-%S")
TODAY:=$(shell date -u +"%Y-%m-%d")

.PHONY: update
update: update-regions-info
	poetry run python get_ebs_pricing.py aws aws-cn aws-us-gov
	echo $(NOW) > docs/last_checked

.PHONY: update-regions-info
update-regions-info:
	wget https://raw.githubusercontent.com/boto/botocore/develop/botocore/data/endpoints.json -O docs/endpoints.json
	for p in $$(cat docs/endpoints.json | jq -r '.partitions[].partition'); do \
		cat docs/endpoints.json | jq -r ".partitions[] | select(.partition==\"$$p\") | .regions" > docs/$$p.regions.json ; \
		done
