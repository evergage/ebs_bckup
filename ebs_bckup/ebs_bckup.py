import ConfigParser
import datetime

import boto3

config = ConfigParser.RawConfigParser()
config.read('./vars.ini')

print('Starting EBS snapshots')


def lambda_handler(event, context):
    regions_str = config.get('regions', 'regionList')
    regions_list = regions_str.split(',')
    ec2_instance_tag_value = config.get('main', 'EC2_INSTANCE_TAG_VALUE')
    ec2_instance_tag_name = config.get('main', 'EC2_INSTANCE_TAG_NAME')
    volume_tag_names_to_retain = config.get('main', 'VOLUME_TAG_NAMES_TO_RETAIN').split(',')
    retention_days = config.getint('main', 'RETENTION_DAYS')

    def snapshot_region(aws_region):
        print("Snapshotting EBS volumes in %s" % aws_region)
        account = event['account']
        ec = boto3.client('ec2', region_name=aws_region)
        instances = find_all_eligible_instances(ec)

        for instance in instances:
            snapshot_instance(ec, instance)

        purge_old_snapshots(account, ec)

    def find_all_eligible_instances(ec):
        reservations = ec.describe_instances(
            Filters=[
                {'Name': 'tag:%s' % ec2_instance_tag_name, 'Values': [ec2_instance_tag_value]},
            ]
        )['Reservations']
        return sum(
            [
                [i for i in reservation['Instances']]
                for reservation in reservations
            ], [])

    def snapshot_instance(ec, instance):
        for dev in instance['BlockDeviceMappings']:
            if dev.get('Ebs', None) is None:
                # skip non EBS volumes
                continue
            snapshot_ebs_volume(ec, instance, dev)

    def snapshot_ebs_volume(ec, instance, dev):
        instance_id = instance['InstanceId']
        instance_name = find_name_tag(instance)

        vol_id = dev['Ebs']['VolumeId']
        vol_tags_response = ec.describe_tags(
            Filters=[{'Name': 'resource-id', 'Values': [vol_id]}],
        )
        vol_name = find_name_tag(vol_tags_response)

        print("Found EBS volume %s (%s) on instance %s (%s), creating snapshot" % (
            vol_name, vol_id, instance_name, instance_id))

        snap = ec.create_snapshot(
            Description="%s from instance %s (%s)" % (vol_name or vol_id, instance_name, instance_id),
            VolumeId=vol_id,
        )

        today_string = str(datetime.date.today())

        snapshot_name = "%s_%s" % (vol_name or vol_id, today_string)
        snapshot_tags = [
            {'Key': 'Name', 'Value': snapshot_name},
            {'Key': 'InstanceId', 'Value': instance_id},
            {'Key': 'InstanceName', 'Value': instance_name},
            {'Key': 'VolumeName', 'Value': vol_name},
            {'Key': 'DeviceName', 'Value': dev['DeviceName']},
            {'key': 'BackupDate', 'Value': today_string},
            {'Key': 'LambdaManagedSnapshot', 'Value': 'true'},
        ]

        transfer_eligible_tags_from_volume(snapshot_tags, vol_tags_response)

        ec.create_tags(
            Resources=[snap['SnapshotId']],
            Tags=snapshot_tags,
        )

    def find_name_tag(object_with_tags):
        name = ''
        for tag in object_with_tags['Tags']:
            if tag["Key"] == 'Name':
                name = tag["Value"]
        return name

    def transfer_eligible_tags_from_volume(snapshot_tags, vol_tags_response):
        for vol_tag_name in volume_tag_names_to_retain:
            for tag in vol_tags_response['Tags']:
                if tag['Key'] == vol_tag_name:
                    snapshot_tags.append({'Key': tag['Key'], 'Value': tag['Value']})

    def purge_old_snapshots(account, ec):
        all_managed_snapshots = ec.describe_snapshots(
            OwnerIds=['%s' % account],
            Filters=[
                {'Name': 'tag:LambdaManagedSnapshot', 'Values': ['true']},
            ],
        )

        ascending_start_dates_to_delete = find_start_dates_to_delete(all_managed_snapshots)

        if len(ascending_start_dates_to_delete) > 0:
            last_start_date_to_delete = ascending_start_dates_to_delete[-1]

            delete_snapshots_older_than(ec, last_start_date_to_delete, all_managed_snapshots)

    def find_start_dates_to_delete(all_managed_snapshots):
        start_dates_set = set()
        for snap in all_managed_snapshots['Snapshots']:
            start_dates_set.add(snap['StartTime'].date())

        ascending_start_dates_to_delete = sorted(start_dates_set)[:-retention_days]

        print("Found distinct days: %d, retention is set at %d days, deleting snapshots made on or before day: %s" % (
            len(start_dates_set), retention_days, str(ascending_start_dates_to_delete)))

        return ascending_start_dates_to_delete

    def delete_snapshots_older_than(ec, last_start_date_to_delete, all_managed_snapshots):
        deleted_snapshots_count = 0

        for snap in all_managed_snapshots['Snapshots']:
            if snap['StartTime'].date() <= last_start_date_to_delete:
                print("Deleting old snapshot %s (started on: %s)" % (snap['SnapshotId'], str(snap['StartTime'])))
                ec.delete_snapshot(SnapshotId=snap['SnapshotId'])
                deleted_snapshots_count += 1

        print("Deleted %d snapshots older than %s" % (deleted_snapshots_count, str(last_start_date_to_delete)))

    for r in regions_list:
        snapshot_region(r)
