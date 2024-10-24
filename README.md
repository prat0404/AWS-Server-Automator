# aws-server-automation
This python 3 script automates the setup of an AWS web server. 


## Introduction
Utilising AWS Boto3, this Python 3 script automates and greatly simplifies the setup of a web server in your AWS account.
The script launches an EC2 instance, creates an S3 bucket, deploys a basic website and sets up a Cloudwatch alarm to ensure the billing does not exceed a certain balance.


## Setup 
1. Create an account on AWS
2. Add your AWS credentials to `~/.aws/credentials`
3. Ensure Python 3 and Boto 3 library are installed locally
4. Create an SSH pair and add the key name to the script
5. Update other variables at the top of the script with your own details including AMI and username

## Instructions
1. clone repository
2. Ensure monitoring.sh and devops_1.py are stored in the same directory
3. Run the script using `python3 devops_1.py`in the command line
4. Troubleshoot via error messages provided by the error handlers in the command line as needed
