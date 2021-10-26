Observations as of 2021-10-25:

```
$ cat prices.json | jq -s '. | length'
350

# - sanity checks -
$ cat prices.json | jq '.serviceCode' | sort | uniq -c
 350 "AmazonEC2"
$ cat prices.json | jq '.product.productFamily' | sort | uniq -c
  26 "Provisioned Throughput"
 198 "Storage"
 126 "System Operation"
```

Each record is tagged with a volume type under `.product.attributes.volumeApiName`. There are currently seven volume types:
```
$ cat prices.json | jq '.product.attributes.volumeApiName' | sort | uniq -c
  52 "gp2"
  78 "gp3"
  52 "io1"
  64 "io2"
  26 "sc1"
  26 "st1"
  52 "standard"
$ cat prices.json | jq '.product.attributes.volumeApiName' | wc -l
     350
```

All of these volume types have the "Storage" component (prices associated with how much storage is allocated):
```
$ cat prices.json | jq 'select( .product.productFamily == "Storage")' | jq '.product.attributes.volumeApiName' | sort |  uniq -c
  52 "gp2"
  26 "gp3"
  26 "io1"
  16 "io2"
  26 "sc1"
  26 "st1"
  26 "standard"
$ cat prices.json | jq 'select( .product.productFamily == "Storage")' | jq '.product.attributes.volumeApiName' | wc -l
     198
```

Currently, four volume types (gp3, io1, io2, and standard) have the "System Operation" component (price associated with IOPS on the EBS volume.):
```
$ cat prices.json | jq 'select( .product.productFamily == "System Operation")' | jq '.product.attributes.volumeApiName' | sort |  uniq -c
  26 "gp3"
  26 "io1"
  48 "io2"
  26 "standard"
$ cat prices.json | jq 'select( .product.productFamily == "System Operation")' | jq '.product.attributes.volumeApiName' | wc -l
     126
```

Currently, one volume type (gp3) has the "Provisioned Throughput" component (price associated with provisioned throughput on the EBS volume.):
```
$ cat prices.json | jq 'select( .product.productFamily == "Provisioned Throughput")' | jq '.product.attributes.volumeApiName' | sort |  uniq -c
  26 "gp3"
```

There are multiple tiers on IOPS, and these are found under ".product.attributes.group":
```
$ cat prices.json | jq 'select( .product.productFamily == "System Operation")' | jq '.product.attributes.group' | sort |  uniq -c
  26 "EBS I/O Requests"
  16 "EBS IOPS Tier 2"
  16 "EBS IOPS Tier 3"
  68 "EBS IOPS"
```

All the prices are OnDemand:
```
$ cat prices.json | jq '.terms | keys' | jq '.[]' | uniq -c
 350 "OnDemand"
```

