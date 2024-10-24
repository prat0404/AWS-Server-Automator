#!/usr/bin/python

import boto3
from datetime import datetime, timedelta
import webbrowser
import time
import sys
import json
import subprocess
import requests
import os

ec2 = boto3.resource('ec2')
cloudwatch = boto3.resource('cloudwatch')
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
username = "USERNAME HERE"
security_group_name = f"security-group-{timestamp}"
ami = "AMI HERE"
websites_file = "your-websites.txt"
key_name = "YOUR KEY NAME HERE"
email = "EMAIL HERE"


def main():
    print(f"***AWS SERVER SETUP STARTED***")
    print(f"- - - - - - - - - - - - - - - - - - ")
    print(f"LAUNCHING EC2 INSTANCE - - -")
    print(f"- - - - - - - - - - - - - - - - - - ")    
    public_ip, instance_id = create_instance()
    print(f"- - - - - - - - - - - - - - - - - - ") 
    print(f"OPEN EC2 INSTANCE URL - - -")
    print(f"- - - - - - - - - - - - - - - - - - ")    
    open_ec2_website(public_ip) 
    print(f"- - - - - - - - - - - - - - - - - - ")  
    print(f"CREATING S3 BUCKET - - -")
    print(f"- - - - - - - - - - - - - - - - - - ")
    create_bucket()
    print(f"- - - - - - - - - - - - - - - - - - ")
    print(f"STARTING INSTANCE MONITORING - - -")
    print(f"- - - - - - - - - - - - - - - - - - ")
    monitor_instance(public_ip)
    print(f"- - - - - - - - - - - - - - - - - - ")
    print(f"RUNNING CLOUDWATCH - - -")
    print(f"- - - - - - - - - - - - - - - - - - ")
    run_cloudwatch(instance_id)
    print(f"- - - - - - - - - - - - - - - - - - ")
    print(f"CREATING CLOUDWATCH BILLING ALARM - - -")
    print(f"- - - - - - - - - - - - - - - - - - ")
    create_ec2_alarm(instance_id)
    print(f"- - - - - - - - - - - - - - - - - - ")
    print(f"***SERVER SETUP COMPLETE***")

#EC2 INSTANCE SETTINGS
#security group setup
security_group = ec2.create_security_group(
    Description='security group',
    GroupName=security_group_name,
)

# Authorize ingress rules using the resource object
security_group.authorize_ingress(
    IpProtocol='tcp',
    FromPort=22,
    ToPort=22,
    CidrIp='0.0.0.0/0'
)

security_group.authorize_ingress(
    IpProtocol='tcp',
    FromPort=80,
    ToPort=80,
    CidrIp='0.0.0.0/0'
)

# Define the user data
user_data=f"""#!/bin/bash
yum update -y
yum install httpd -y
systemctl enable httpd
systemctl start httpd

# Get instance metadata
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
instance_id=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
instance_type=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-type)
availability_zone=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)
public_ip=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)

# Write HTML content to index.html
echo "<h1>/Instance</h1>" > index.html
echo "<h2>This is a test instance created as part of DevOps Assignment 1</h2>" >> index.html
echo "<br>" >> index.html
echo "<h3>INSTANCE METADATA</h3>" >> index.html
echo "<p>-----------------</p>" >> index.html
echo "<p><b>Instance ID:</b> $instance_id </p>" >> index.html
echo "<p><b>Instance Type:</b> $instance_type </p>" >> index.html
echo "<p><b>Instance Availability Zone:</b> $availability_zone </p>" >> index.html
echo "<p><b>Instance Public IPv4:</b> $public_ip </p>" >> index.html
mv index.html /var/www/html
"""

def create_instance():
    # Creating instance
    print("creating EC2 instance")
    try:
        new_instances = ec2.create_instances(
            ImageId=ami,
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.nano',
            SecurityGroupIds=[
                security_group.id
            ],
            KeyName=key_name,
            UserData=user_data,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Owner',
                            'Value': username
                        },
                        {
                            'Key': 'Name',
                            'Value': 'web server'
                        }
                    ]
                }
            ]
        )
        print("Instance created:", new_instances[0].id)
    except Exception as e:
        print("An error occurred when creating the instance:", e)
        
    # Pauses program until instance running and refreshes
    print("Waiting on instance to be running...")
    new_instances[0].wait_until_running()
    new_instances[0].reload()
    print("instance running")

    public_ip = new_instances[0].public_ip_address
    instance_id = new_instances[0].id
    
    # writing ec2 url to log file
    print("writing ec2 URL to log file")
    try:
        url_string = f"ec2 URL: http://{public_ip}/index.html \n"
        with open(websites_file, "w") as file:
            file.write(url_string)
    except Exception as e:
        print("An error occurred when writing EC2 url to log file:", e)
            
    return public_ip, instance_id

def open_ec2_website(public_ip):
    # Waits for user data script to complete then opens apache server in browser
    count = 0
    while True:
        try:
            response = requests.get(f'http://{public_ip}/index.html')
            print("checking website status")
            if response.status_code == 200:
                print("instance server opening in browser...")
                webbrowser.open_new_tab(f'http://{public_ip}/index.html')
                return True
        except Exception as e:
            count += 1
            print("Trying to open server, try ", count)
            time.sleep(5)
            if count >= 10:
                print("An error occurred when open instance server in browser:", e)
                break




def create_bucket():
# Creating s3 bucket
    s3 = boto3.resource('s3')
    bucket_name = f"{timestamp}-{username}"
    try:
        response = s3.create_bucket(Bucket=bucket_name)
        print (f"bucket created. Name: {bucket_name}")
    except Exception as e:
        print("An error occurred when creating the bucket:", e)
        
# Clear block public access
    s3client = boto3.client('s3')
    s3client.delete_public_access_block(Bucket=bucket_name)
    
# Define the bucket policy
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }

# Apply the bucket policy
    s3.Bucket(bucket_name).Policy().put(Policy=json.dumps(bucket_policy))

## Enable static website hosting
    website_configuration = {
        'ErrorDocument': {'Key': 'error.html'},
        'IndexDocument': {'Suffix': 'index.html'},
    }
    bucket_website = s3.BucketWebsite(bucket_name)
    response = bucket_website.put(WebsiteConfiguration=website_configuration)
      
    # download image for bucket
    # code for using request module adapted from here https://stackoverflow.com/questions/13137817/how-to-download-image-using-requests
    print("getting image for uploading to bucket")
    image = "logo.jpg"
    url = f"http://devops.witdemo.net/{image}"
    try:
        r = requests.get(url)
        with open(image, "wb") as file:
            file.write(r.content)
        print("image downloaded")
    except Exception as e:
        print("An error occurred when downloading the image:", e)
    
    # upload image to bucket
    print("uploading image to bucket")
    try:
        s3.Object(bucket_name, image).put(Body=open(image, 'rb'), ContentType='image/jpg')
        print("file added to bucket")
    except Exception as e:
        print("An error occurred when uploading to bucket:", e)
    
    # add file to s3 index.html file
    print("creating index.html with image in bucket")
    filepath = "index.html"
    content = f"<img src='https://{bucket_name}.s3.amazonaws.com/{image}'>"
    try:
        with open(filepath, "w") as file:
            file.write(content)
        print("index.html created with s3 object url added")
    except Exception as e:
        print("An error occurred when downloading the image:", e)
    
    # upload index.html to s3
    print("uploading index.html to s3")
    try:
        s3.Object(bucket_name, filepath).put(Body=open(filepath, 'rb'), ContentType='text/html')
        print("file added to bucket")
    except Exception as e:
        print("An error occurred when uploading to bucket:", e)
    

    # opening bucket url in browser    
    try:
        print("s3 url opening in browser...")
        webbrowser.open_new_tab(f'http://{bucket_name}.s3-website-us-east-1.amazonaws.com/')
    except Exception as e:
        print("An error occurred when open s3 url in browser:", e)
    
    # writing s3 url to log file
    # code for appending found here: https://www.geeksforgeeks.org/python-append-to-a-file/
    print("writing s3 URL to log file")
    try:
        url_string = f"s3 URL: http://{bucket_name}.s3-website-us-east-1.amazonaws.com/"
        with open(websites_file, "a") as file:
            file.write(url_string)
    except Exception as e:
        print("An error occurred when writing s3 url to log file:", e)

def monitor_instance(public_ip):
    # copy script to instance
    try:
        print("copying monitoring script to instance")
        subprocess.run(["scp", "-i", f"{key_name}.pem", "-o", "StrictHostKeyChecking=no", "monitoring.sh", f"ec2-user@{public_ip}:."], check=True)
    except Exception as e:
        print("An error occurred when copying script to instance", e)
    
    # set permissions for script in instance
    try:
        print("setting permissions for monitoring script")
        subprocess.run(["ssh", "-i", f"{key_name}.pem", "-o", "StrictHostKeyChecking=no", f"ec2-user@{public_ip}", f"chmod 700 ~/monitoring.sh"], check=True)
    except Exception as e:
        print("An error occurred when setting monitoring script permissions", e)
        
    # Run monitoring script
    try:
        print("Running monitoring script")
        subprocess.run(["ssh", "-i", f"{key_name}.pem", "-o", "StrictHostKeyChecking=no", f"ec2-user@{public_ip}", "./monitoring.sh"], check=True)
    except Exception as e:
        print("An error occurred when running script", e)

def run_cloudwatch(instance_id):
    instance = ec2.Instance(instance_id)
    instance.reload()
    instance.monitor()
    print("sleeping for 5 minutes while metrics measured...")
    time.sleep(360)

    # CPU Utilization metrics
    cpu_metric_iterator = cloudwatch.metrics.filter(Namespace='AWS/EC2',
                                                     MetricName='CPUUtilization',
                                                     Dimensions=[{'Name':'InstanceId', 'Value': instance_id}])
    # NetworkOut metrics
    network_out_metric_iterator = cloudwatch.metrics.filter(Namespace='AWS/EC2',
                                                             MetricName='NetworkOut',
                                                             Dimensions=[{'Name':'InstanceId', 'Value': instance_id}])
    # Get CPUUtilization metric
    cpu_metric = list(cpu_metric_iterator)[0]
    cpu_response = cpu_metric.get_statistics(StartTime=datetime.utcnow() - timedelta(minutes=5),
                                             EndTime=datetime.utcnow(),
                                             Period=300,
                                             Statistics=['Average'])

    # Get NetworkOut metric
    network_out_metric = list(network_out_metric_iterator)[0]
    network_out_response = network_out_metric.get_statistics(StartTime=datetime.utcnow() - timedelta(minutes=5),
                                                             EndTime=datetime.utcnow(),
                                                             Period=300,
                                                             Statistics=['Average'])
    # Print results
    if 'Datapoints' in cpu_response:
        print("Average CPU utilization:", cpu_response['Datapoints'][0]['Average'], cpu_response['Datapoints'][0]['Unit'])
    else:
        print("No CPU utilization data available.")

    # Print NetworkOut results
    if 'Datapoints' in network_out_response:
        print("Average NetworkOut:", network_out_response['Datapoints'][0]['Average'], network_out_response['Datapoints'][0]['Unit'])
    else:
        print("No NetworkOut data available.")
    print(cpu_response) 
    print(network_out_response)

# code for setting alarm etc: https://stackoverflow.com/questions/68323101/aws-billing-alerts-send-email-and-trigger-lambda-function
def create_ec2_alarm(instance_id):
    cloudwatch = boto3.client('cloudwatch')
    
    # Create SNS topic
    sns_client = boto3.client('sns')
    response = sns_client.create_topic(Name='EC2BillingAlarmTopic')
    sns_topic_arn = response['TopicArn']
    
    # Subscribe email address to SNS topic
    sns_client.subscribe(
        TopicArn=sns_topic_arn,
        Protocol='email',
        Endpoint=email
    )
    
    # alarm properties
    # generated on cloudwatch backend
    alarm_properties = {
        "AlarmName": f"ec2-{instance_id}-5dollar-alarm",
        "ActionsEnabled": True,
        "OKActions": [],
        "AlarmActions": [
            sns_topic_arn  # Using the SNS topic ARN
        ],
        "InsufficientDataActions": [],
        "MetricName": "EstimatedCharges",
        "Namespace": "AWS/Billing",
        "Statistic": "Maximum",
        "Dimensions": [
            {
                "Name": "ServiceName",
                "Value": "AmazonEC2"
            },
            {
                "Name": "Currency",
                "Value": "USD"
            },
            {
                "Name": "InstanceId",
                "Value": instance_id
            }
        ],
        "Period": 21600,
        "EvaluationPeriods": 1,
        "DatapointsToAlarm": 1,
        "Threshold": 5,
        "ComparisonOperator": "GreaterThanThreshold",
        "TreatMissingData": "missing"
    }
    
    # Create alarm
    try:
        response = cloudwatch.put_metric_alarm(**alarm_properties)
        print("Alarm created:", response)
        print("------------")
        print("alarm will notify if instance billing >5 dollar after 6 hrs")
    except Exception as e:
        print("An error occurred when creating the alarm:", e)

    
    

# Boilerplate call of main() function.
if __name__ == '__main__':
    main()