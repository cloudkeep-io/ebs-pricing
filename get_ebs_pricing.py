import sys
import boto3
import json
from collections import defaultdict
from tools import boto3_paginate

VOL_TYPES = {
    "gp2": {
        "description": "General Purpose"
    },
    "io1": {
        "description": "Provisioned IOPS"
    },
    "st1": {
        "description": "Throughput Optimized HDD"
    },
    "sc1": {
        "description": "Cold HDD"
    },
    "standard": {
        "description": "Magnetic"
    },
}


def get_price_map():
    client = boto3.client('pricing')

    prices = [json.loads(response) for response in boto3_paginate(
        client.get_products,
        ServiceCode='AmazonEC2',
        Filters=[
            {
                'Type': 'TERM_MATCH',
                'Field': 'productFamily',
                'Value': 'Storage'
            },
        ],
        FormatVersion='aws_v1'
    )]

    prices.extend([json.loads(response) for response in boto3_paginate(
        client.get_products,
        ServiceCode='AmazonEC2',
        Filters=[
            {
                'Type': 'TERM_MATCH',
                'Field': 'productFamily',
                'Value': 'System Operation'
            },
        ],
        FormatVersion='aws_v1'
    )])

    return {price["product"]["sku"]: price for price in prices}


def get_ebs_price_map(price_map, regions):
    ebs_price_map = defaultdict(lambda: defaultdict(lambda: defaultdict(str)))

    for vol_type in VOL_TYPES:
        for region_id in regions:
            for sku in price_map:
                price = price_map[sku]

                if (price["product"]["productFamily"] == "Storage" and
                    price["product"]["attributes"].get("volumeType")
                        == VOL_TYPES[vol_type]["description"] and
                    price["product"]["attributes"]["location"]
                        == regions[region_id]["description"]):

                    tids = list(price["terms"]["OnDemand"].keys())
                    assert len(tids) == 1, "not exactly one ondemand term"
                    pds = (
                        price["terms"]["OnDemand"][tids[0]]["priceDimensions"]
                    )
                    pdids = list(pds.keys())
                    assert len(tids) == 1, "not exactly one price dimension"
                    assert pds[pdids[0]]["unit"] in ["GB-Mo", "GB-month"], \
                        "unit != [GB-Mo, GB-month]"
                    ebs_price_map[vol_type][region_id]["price_per_GiB"] = (
                        pds[pdids[0]]["pricePerUnit"]
                    )

                if (vol_type == "io1" and
                    price["product"]["productFamily"] == "System Operation" and
                    price["product"]["attributes"]["provisioned"] == "Yes" and
                    price["product"]["attributes"]["location"]
                        == regions[region_id]["description"]):

                    tids = list(price["terms"]["OnDemand"].keys())
                    assert len(tids) == 1, "not exactly one ondemand term"
                    pds = (
                        price["terms"]["OnDemand"][tids[0]]["priceDimensions"]
                    )
                    pdids = list(pds.keys())
                    assert len(tids) == 1, "not exactly one price dimension"
                    assert pds[pdids[0]]["unit"] == "IOPS-Mo", \
                        "unit != IOPS-Mo"
                    ebs_price_map[vol_type][region_id]["price_per_PIOPS"] = (
                        pds[pdids[0]]["pricePerUnit"]
                    )

                if (vol_type == "standard" and
                    price["product"]["productFamily"] == "System Operation" and
                    price["product"]["attributes"]["provisioned"] == "No" and
                    price["product"]["attributes"]["location"]
                        == regions[region_id]["description"]):

                    tids = list(price["terms"]["OnDemand"].keys())
                    assert len(tids) == 1, "not exactly one ondemand term"
                    pds = (
                        price["terms"]["OnDemand"][tids[0]]["priceDimensions"]
                    )
                    pdids = list(pds.keys())
                    assert len(tids) == 1, "not exactly one price dimension"
                    assert pds[pdids[0]]["unit"] == "IOs", "unit != IOs"
                    ebs_price_map[vol_type][region_id]["price_per_IO"] = (
                        pds[pdids[0]]["pricePerUnit"]
                    )

    return ebs_price_map


if __name__ == '__main__':

    price_map = get_price_map()

    for partition in sys.argv[1:]:

        with open(f"docs/{partition}.regions.json") as f:
            regions = json.load(f)

        ebs_price_map = get_ebs_price_map(price_map, regions)

        with open(f"docs/{partition}.ebs_pricing.json", 'w') as g:
            g.write(json.dumps(ebs_price_map, sort_keys=True, indent=4))
