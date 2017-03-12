import logging

from awacs import (
    awslambda,
    ecs,
    ec2,
    events,
    iam,
    route53,
    kinesis,
    sns,
    logs,
    sqs,
    s3,
    cloudformation,
    elasticloadbalancing as elb,
    ecr,
)
from awacs.aws import (
    Statement,
    Allow,
    Policy,
    Action,
    Principal,
    Condition,
    SourceArn,
    ArnEquals,
)
from troposphere import (
    Ref,
    Join,
)

logger = logging.getLogger(__name__)


def ecs_agent_policy():
    p = Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Resource=["*"],
                Action=[
                    ecs.CreateCluster,
                    ecs.RegisterContainerInstance,
                    ecs.DeregisterContainerInstance,
                    ecs.DiscoverPollEndpoint,
                    ecs.Action("Submit*"),
                    ecs.Poll,
                    ecs.Action("StartTelemetrySession")]),
            Statement(
                Effect=Allow,
                Action=[
                    ecr.GetAuthorizationToken,
                    ecr.BatchCheckLayerAvailability,
                    ecr.GetDownloadUrlForLayer,
                    ecr.BatchGetImage,
                ],
                Resource=["*"],
            ),
        ]
    )

    return p


def service_role_policy():
    p = Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Resource=["*"],
                Action=[
                    ec2.AuthorizeSecurityGroupIngress,
                    Action("ec2", "Describe*"),
                    elb.DeregisterInstancesFromLoadBalancer,
                    Action("elasticloadbalancing", "Describe*"),
                    elb.RegisterInstancesWithLoadBalancer,
                    elb.Action("RegisterTargets"),
                    elb.Action("DeregisterTargets"),
                ]
            )
        ]
    )
    return p


def empire_policy(resources):
    p = Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Resource=[resources['CustomResourcesTopic']],
                Action=[sns.Publish]),
            Statement(
                Effect=Allow,
                Resource=[resources['CustomResourcesQueue']],
                Action=[
                    sqs.ReceiveMessage,
                    sqs.DeleteMessage,
                    sqs.ChangeMessageVisibility
                ]),
            Statement(
                Effect=Allow,
                Resource=[resources['TemplateBucket']],
                Action=[
                    s3.PutObject,
                    s3.PutObjectAcl,
                    s3.PutObjectVersionAcl,
                    s3.GetObject,
                    s3.GetObjectVersion,
                    s3.GetObjectAcl,
                    s3.GetObjectVersionAcl]),
            Statement(
                Effect=Allow,
                Resource=["*"],
                Action=[
                    awslambda.CreateFunction,
                    awslambda.DeleteFunction,
                    awslambda.UpdateFunctionCode,
                    awslambda.GetFunctionConfiguration,
                    awslambda.AddPermission,
                    awslambda.RemovePermission]),
            Statement(
                Effect=Allow,
                Resource=["*"],
                Action=[
                    events.PutRule,
                    events.DeleteRule,
                    events.DescribeRule,
                    events.EnableRule,
                    events.DisableRule,
                    events.PutTargets,
                    events.RemoveTargets]),
            Statement(
                Effect=Allow,
                Resource=[
                    Join('', [
                        'arn:aws:cloudformation:', Ref('AWS::Region'), ':',
                        Ref('AWS::AccountId'), ':stack/',
                        resources['Environment'], '-*'])],
                Action=[
                    cloudformation.CreateStack,
                    cloudformation.UpdateStack,
                    cloudformation.DeleteStack,
                    cloudformation.ListStackResources,
                    cloudformation.DescribeStackResource,
                    cloudformation.DescribeStacks]),
            Statement(
                Effect=Allow,
                Resource=['*'],
                Action=[cloudformation.ValidateTemplate]),
            Statement(
                Effect=Allow,
                Resource=["*"],
                Action=[ecs.CreateService, ecs.DeleteService,
                        ecs.DeregisterTaskDefinition,
                        ecs.Action("Describe*"), ecs.Action("List*"),
                        ecs.RegisterTaskDefinition, ecs.RunTask,
                        ecs.StartTask, ecs.StopTask, ecs.SubmitTaskStateChange,
                        ecs.UpdateService]),
            Statement(
                Effect=Allow,
                # TODO: Limit to specific ELB?
                Resource=["*"],
                Action=[
                    elb.Action("Describe*"),
                    elb.AddTags,
                    elb.CreateLoadBalancer,
                    elb.CreateLoadBalancerListeners,
                    elb.DescribeTags,
                    elb.DeleteLoadBalancer,
                    elb.ConfigureHealthCheck,
                    elb.ModifyLoadBalancerAttributes,
                    elb.SetLoadBalancerListenerSSLCertificate,
                    elb.SetLoadBalancerPoliciesOfListener,
                    elb.Action("CreateTargetGroup"),
                    elb.Action("CreateListener"),
                    elb.Action("DeleteListener"),
                    elb.Action("DeleteTargetGroup"),
                    elb.Action("ModifyTargetGroup"),
                    elb.Action("ModifyTargetGroupAttributes"),
                ]
            ),
            Statement(
                Effect=Allow,
                Resource=["*"],
                Action=[ec2.DescribeSubnets, ec2.DescribeSecurityGroups]
            ),
            Statement(
                Effect=Allow,
                Action=[iam.GetServerCertificate, iam.UploadServerCertificate,
                        iam.DeleteServerCertificate, iam.PassRole],
                Resource=["*"]
            ),
            Statement(
                Effect=Allow,
                Action=[
                    Action("route53", "ListHostedZonesByName"),
                    route53.ChangeResourceRecordSets,
                    route53.ListHostedZones,
                    route53.GetHostedZone,
                    route53.GetChange,
                ],
                # TODO: Limit to specific zones
                Resource=["*"]
            ),
            Statement(
                Effect=Allow,
                Action=[
                    kinesis.DescribeStream,
                    Action(kinesis.prefix, "Get*"),
                    Action(kinesis.prefix, "List*"),
                    kinesis.PutRecord,
                ],
                Resource=["*"]
            ),
            Statement(
                Effect=Allow,
                Action=[
                    ecr.GetAuthorizationToken,
                    ecr.BatchCheckLayerAvailability,
                    ecr.GetDownloadUrlForLayer,
                    ecr.BatchGetImage,
                ],
                Resource=["*"],
            ),
        ]
    )
    return p


def sns_events_policy(topic_arn):
    p = Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Action=[sns.Publish],
                Resource=[topic_arn],
            )])

    return p


def logstream_policy():
    """Policy needed for logspout -> kinesis log streaming."""
    p = Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Resource=["*"],
                Action=[
                    kinesis.CreateStream, kinesis.DescribeStream,
                    Action(kinesis.prefix, "AddTagsToStream"),
                    Action(kinesis.prefix, "PutRecords")
                ])])
    return p


def runlogs_policy(log_group_ref):
    """Policy needed for Empire -> Cloudwatch logs to record run output."""
    p = Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Resource=[
                    Join('', [
                        'arn:aws:logs:*:*:log-group:',
                        log_group_ref,
                        ':log-stream:*'])],
                Action=[
                    logs.CreateLogStream,
                    logs.PutLogEvents,
                ])])
    return p


def sns_to_sqs_policy(topic):
    p = Policy(
        Statement=[
            Statement(
                Effect=Allow,
                Principal=Principal('*'),
                Action=[sqs.SendMessage],
                Resource=["*"],
                Condition=Condition(ArnEquals(SourceArn, topic)))])
    return p
