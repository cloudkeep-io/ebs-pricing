import boto3
import json
from collections import defaultdict
from tools import boto3_paginate

# Currently supported Volume Types
VOL_TYPES = {'gp2', 'gp3', 'io1', 'io2', 'sc1', 'st1', 'standard'}
PRODUCT_FAMILIES = ['Storage', 'System Operation', 'Provisioned Throughput']


def pricing_get_ebs_prices():
    client = boto3.client('pricing')

    prices = []
    for product_family in PRODUCT_FAMILIES:
        prices.extend([json.loads(response) for response in boto3_paginate(
            client.get_products,
            ServiceCode='AmazonEC2',
            Filters=[
                {
                    'Type': 'TERM_MATCH',
                    'Field': 'productFamily',
                    'Value': product_family
                },
            ],
            FormatVersion='aws_v1'
        )])

    return prices


def ssm_get_rz_info():
    client = boto3.client('ssm')
    rz_info = {}

    # gather info for regions
    regions = boto3_paginate(
        client.get_parameters_by_path,
        Path='/aws/service/global-infrastructure/regions'
    )
    for region in regions:
        response = client.get_parameter(Name=f"{region['Name']}/longName")
        longName = response['Parameter']['Value']
        location = longName.replace("Europe", "EU").replace('\u2013', '-')
        response = client.get_parameter(Name=f"{region['Name']}/partition")
        partition = response['Parameter']['Value']
        rz_info[region['Value']] = {
            'location': location,
            'rzType': "region",
            'partition': partition
        }

    # gather info for local zones
    lzs = boto3_paginate(
        client.get_parameters_by_path,
        Path='/aws/service/global-infrastructure/local-zones'
    )
    for lz in lzs:
        response = client.get_parameter(Name=f"{lz['Name']}/location")
        rz_info[lz['Value']] = {
            'location': response['Parameter']['Value'].replace('\u2013', '-'),
            'rzType': "local_zone"
        }

    # gather info for wavelength zones
    wzs = boto3_paginate(
        client.get_parameters_by_path,
        Path='/aws/service/global-infrastructure/wavelength-zones'
    )
    for wz in wzs:
        response = client.get_parameter(Name=f"{wz['Name']}/location")
        rz_info[wz['Value']] = {
            'location': response['Parameter']['Value'].replace('\u2013', '-'),
            'rzType': "wavelength_zone"
        }

    return rz_info


def get_price_per_unit(units, price):
    ondemand_terms = list(price["terms"]["OnDemand"].values())
    assert len(ondemand_terms) == 1, "expected exactly one on-demand term"

    price_dimensions = list(ondemand_terms[0]['priceDimensions'].values())
    assert len(price_dimensions) == 1, "expected exactly one price dimensions"
    assert price_dimensions[0]['unit'] in units, \
        f"expected unit to be in {units}, got {price_dimensions[0]['unit']}"

    return price_dimensions[0]['pricePerUnit']


def add_gp2_pricing(ebs_prices, prices):
    if not prices:
        return

    assert len(prices) == 1, "gp2 pricing should only have one dimension"
    ebs_prices['gp2'] = {}
    for price in prices:
        ebs_prices['gp2']['pricePerGBMonth'] = \
            get_price_per_unit(["GB-Mo", "GB-month"], price)


def add_gp3_pricing(ebs_prices, prices):
    if not prices:
        return

    assert len(prices) == 3, "gp3 pricing should have three dimensions"
    ebs_prices['gp3'] = {}

    for price in prices:

        if price['product']['productFamily'] == 'Storage':
            ebs_prices['gp3']['pricePerGBMonth'] = \
                get_price_per_unit(["GB-Mo", "GB-month"], price)

        elif price['product']['productFamily'] == 'System Operation':
            ebs_prices['gp3']['pricePerIOPSMonth'] = \
                get_price_per_unit(["IOPS-Mo"], price)

        elif price['product']['productFamily'] == 'Provisioned Throughput':
            ebs_prices['gp3']['pricePerGiBpsMonth'] = \
                get_price_per_unit(["GiBps-mo"], price)


def add_io1_pricing(ebs_prices, prices):
    if not prices:
        return

    assert len(prices) == 2, "io1 pricing should have two dimensions"
    ebs_prices['io1'] = {}

    for price in prices:

        if price['product']['productFamily'] == 'Storage':
            ebs_prices['io1']['pricePerGBMonth'] = \
                get_price_per_unit(["GB-Mo", "GB-month"], price)

        elif price['product']['productFamily'] == 'System Operation':
            ebs_prices['io1']['pricePerIOPSMonth'] = \
                get_price_per_unit(["IOPS-Mo"], price)


def add_io2_pricing(ebs_prices, prices):
    if not prices:
        return

    assert len(prices) == 4, "io1 pricing should have four dimensions"
    ebs_prices['io2'] = {}

    for price in prices:

        if price['product']['productFamily'] == 'Storage':
            ebs_prices['io2']['pricePerGBMonth'] = \
                get_price_per_unit(["GB-Mo", "GB-month"], price)

        elif price['product']['productFamily'] == 'System Operation':

            if price['product']['attributes']['group'] == 'EBS IOPS':
                ebs_prices['io2']['pricePerTier1IOPSMonth'] = \
                    get_price_per_unit(["IOPS-Mo"], price)

            if price['product']['attributes']['group'] == 'EBS IOPS Tier 2':
                ebs_prices['io2']['pricePerTier2IOPSMonth'] = \
                    get_price_per_unit(["IOPS-Mo"], price)

            if price['product']['attributes']['group'] == 'EBS IOPS Tier 3':
                ebs_prices['io2']['pricePerTier3IOPSMonth'] = \
                    get_price_per_unit(["IOPS-Mo"], price)


def add_sc1_pricing(ebs_prices, prices):
    if not prices:
        return

    assert len(prices) == 1, "sc1 pricing should only have one dimension"
    ebs_prices['sc1'] = {}
    for price in prices:
        ebs_prices['sc1']['pricePerGBMonth'] = \
            get_price_per_unit(["GB-Mo", "GB-month"], price)


def add_st1_pricing(ebs_prices, prices):
    if not prices:
        return

    assert len(prices) == 1, "st1 pricing should only have one dimension"
    ebs_prices['st1'] = {}
    for price in prices:
        ebs_prices['st1']['pricePerGBMonth'] = \
            get_price_per_unit(["GB-Mo", "GB-month"], price)


def add_standard_pricing(ebs_prices, prices):
    if not prices:
        return

    assert len(prices) == 2, "standard pricing should have two dimensions"
    ebs_prices['standard'] = {}

    for price in prices:

        if price['product']['productFamily'] == 'Storage':
            ebs_prices['standard']['pricePerGBMonth'] = \
                get_price_per_unit(["GB-Mo", "GB-month"], price)

        elif price['product']['productFamily'] == 'System Operation':
            ebs_prices['standard']['pricePerIOs'] = \
                get_price_per_unit(["IOs"], price)


if __name__ == '__main__':

    # make API calls
    prices = pricing_get_ebs_prices()
    rz_info = ssm_get_rz_info()

    # index into prices based on location and vol_type
    prices_map = defaultdict(list)
    for price in prices:
        vol_type = price['product']['attributes']['volumeApiName']
        location = price['product']['attributes']['location']
        prices_map[(location, vol_type)].append(price)

    # gather all volume types and check against the supported list
    vol_types = {key[1] for key in prices_map.keys()}
    assert vol_types == VOL_TYPES, "Unsupported Volume Type Found"

    # index into rz_info based on rzType and partition
    rz_map = defaultdict(list)
    for rz in rz_info.keys():
        rz_type = rz_info[rz]['rzType']
        partition = rz_info[rz].get('partition')
        rz_map[(rz_type, partition)].append(rz)

    # build ebs_pricing data
    ebs_pricing = []
    for rz_key in rz_map.keys():
        for rz in sorted(rz_map[rz_key]):
            location = rz_info[rz]['location']
            ebs_prices = {}
            add_gp2_pricing(ebs_prices, prices_map[(location, 'gp2')])
            add_gp3_pricing(ebs_prices, prices_map[(location, 'gp3')])
            add_io1_pricing(ebs_prices, prices_map[(location, 'io1')])
            add_io2_pricing(ebs_prices, prices_map[(location, 'io2')])
            add_sc1_pricing(ebs_prices, prices_map[(location, 'sc1')])
            add_st1_pricing(ebs_prices, prices_map[(location, 'st1')])
            add_standard_pricing(ebs_prices,
                                 prices_map[(location, 'standard')])
            rz_ebs_pricing = {
                'rzCode':  rz,
                'location': location,
                'rzType': rz_info[rz]['rzType'],
                'ebs_prices': ebs_prices
            }

            if partition := rz_info[rz].get('partition'):
                rz_ebs_pricing['partition'] = partition

            ebs_pricing.append(rz_ebs_pricing)

    # print the result to stdout
    print(json.dumps(ebs_pricing, sort_keys=True, indent=4))
