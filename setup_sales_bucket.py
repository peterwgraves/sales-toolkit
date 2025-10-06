import boto3
from datetime import datetime

s3 = boto3.client('s3')

# Create a bucket specifically for your sales toolkit
# Must be globally unique - add your initials or random numbers
bucket_name = 'enfi-sales-toolkit-xyz123'  # CHANGE xyz123 to something unique

print(f"Creating sales toolkit bucket: {bucket_name}")

try:
    s3.create_bucket(Bucket=bucket_name)
    print(f"✓ Bucket created!")
    
    # Create folder structure for organization
    folders = [
        'demo-data/',
        'customer-examples/',
        'roi-calculations/',
        'reports/'
    ]
    
    print("\nCreating folder structure...")
    for folder in folders:
        s3.put_object(Bucket=bucket_name, Key=folder)
        print(f"  ✓ {folder}")
    
    print(f"\n✓ Sales toolkit bucket ready: {bucket_name}")
    print("You can use this for all your demo data and tools!")
    
except Exception as e:
    print(f"Error: {e}")
    print("Try a different bucket name (must be globally unique)")