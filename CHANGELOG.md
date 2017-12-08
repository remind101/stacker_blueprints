## 1.0.6 (2017-12-08)

- Add s3:PutObjectVersionAcl action to s3 policies [GH-150]
- Fix sns.py trying to create an sqs policy for non-sqs-type topics [GH-151]
- Fix default for topics with no subscriptions [GH-153]

## 1.0.5 (2017-11-01)

This is a minor release to deal with dependency conflicts between
stacker & stacker\_blueprints, specifically around troposphere & awacs.

## 1.0.4 (2017-10-30)

- Convert SQS Queue blueprint to TroposphereType [GH-132]
- Allow overriding of Code object in aws\_lambda.Function subclasses [GH-133]
- FunctionScheduler (Cloudwatch Events based) blueprint [GH-134]
- route53 VPC private hosted zones [GH-135]
- Add lambda external role support [GH-136]
- Add lambda version support [GH-138]
- Add lambda alias support [GH-139]
- Add stream spec for aws lambda [GH-146]

## 1.0.3 (2017-08-24)

- New iam Roles blueprint [GH-106]
- Add bastion security group output [GH-113]
- Add PutObjectACL action [GH-114]
- Add default db name in RDS [GH-115]
- Fix Elasticache subnets [GH-116]
- Fix issue w/ SnapshotRetnetionLimit [GH-117]
- Add FifoQueue parameter to sqs.Queues [GH-118]
- KMS refactor [GH-119]
- Route53 refactor [GH-120]
- Add ELB hostedZoneId if missing for Alias targets in Route53 [GH-121]
- Generic Resource Creator [GH-122]
- DNS Hosted Zone Comments in Route53 [GH-123]
- Skip record\_set if Enabled key is False [GH-126]
- Make A & CNAME share the same label [GH-127]

## 1.0.2 (2017-05-18)

- Basic VPC Flow Logs blueprint [GH-94]
- Basic KMS Key blueprint [GH-95]
- Updated Firehose blueprints [GH-96]
- Add website url to s3 bucket [GH-97]
- Cloudwatch Log filters blueprint [GH-98]
- Simple Lambda Function blueprint [GH-99]
- Route53 recordset blueprint [GH-102]
- Minor fixes for Aurora blueprints [GH-111]

## 1.0.1 (2017-04-13)

- Update examples to use explicit output lookups [GH-82]
- Fix vpc parameters [GH-83]
- Fix elasticsearch replication group [GH-84]
- Add s3 policies [GH-85]
- Fix bad empire merge [GH-86]
- Remove repeated values [GH-87]
- Fix elasticache template [GH-90]
- Change missed Refs [GH-92]

## 1.0.0 (2017-03-04)

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
