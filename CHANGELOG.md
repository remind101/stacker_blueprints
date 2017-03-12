## 1.0.0 (2016-03-04)

- New low-level security group rule blueprint [GH-56]
- Update firehose blueprint to fully use variables [GH-57]
- convert dynamodb to TroposphereType [GH-58]
- Update elasticache to fully use variables [GH-59]
- Update VPC to fully use variables [GH-60]
- give empire daemon access to ECR [GH-70]
- simple ECS repo blueprint [GH-72]
- update RDS to fully use variables [GH-76]
- Initial aurora blueprints [GH-77]
- s3 blueprint [GH-80]

## 0.7.6 (2017-01-19)

- Fix empire minion ECR access [GH-70]
- Fix SQS Queue Policy issue w/ multiple SQS queues [GH-71]
- Simple ECR repository blueprint [GH-72]

## 0.7.4 (2017-01-06)

- Remove version and family checking from RDS [GH-67]

## 0.7.3 (2016-11-28)

- Add low-level security group rule blueprint [GH-56]
- Relax troposphere dependency [GH-64]

## 0.7.2 (2016-10-19)

- Add Elasticsearch Domain [GH-47]
- Fix namespace issue in firehose blueprint [GH-48]
- Setup flake8 in CI, cleanup bad pep8 blueprnts [GH-50]
- Update empire blueprints to empire 0.11.0 & fix various bugs [GH-51]

## 0.7.1 (2016-09-27)

- Fix typo in RDS base blueprint introduced in GH-29 [GH-44]

## 0.7.0 (2016-09-23)

This is the first release to include blueprints with the new Blueprint Variables
concept introduced in stacker 0.8.

- output EmpireMinionRole [GH-18]
- allow users & groups for firehose [GH-19]
- KMS integration for firehose [GH-20]
- Update empire stacks to use Empire Daemon [GH-22]
- Add test helper for empire stacks [GH-26]
- Allow use of existing security group with RDS [GH-29]
- Move to compatible release versions for all dependencies [GH-30]
- Add SNS, SQS, DynamoDB Blueprints [GH-43]

## 0.6.5 (2016-05-31)

- Fix issue w/ firehose support relying on unreleased awacs features

## 0.6.4 (2016-05-29)

- Make internal zone first in DNS in VPC blueprints [#7]
- Add support for NAT Gateways [#10]
- Add stack to help creating firehose delivery streams [#16]

## 0.6.3 (2016-05-16)

- Add support for ACM certificates
- Add new RDS db versions

## 0.6.2 (2016-02-11)

- Update dependency to include new compatible stacker release 0.6.1

## 0.6.1 (2016-01-24)

- Update empire blueprints & configs for empire 0.10.0 [GH-6]

## 0.6.0 (2016-01-07)

- Pull in recent ASG changes that were merged [GH-2]
- Initial elasticache blueprints [GH-3]
- Fix blank env string change [GH-4]

## 0.5.4 (2015-12-08)

- Initial release
