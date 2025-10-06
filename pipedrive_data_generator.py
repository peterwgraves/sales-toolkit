import boto3
from faker import Faker
import csv
from datetime import datetime, timedelta
from io import StringIO
import random

# Setup
s3 = boto3.client('s3')
fake = Faker()
bucket_name = 'enfi-sales-toolkit-xyz123'

# EnFi-specific data
COMPANY_TYPES = [
    'Credit Union', 'Community Bank', 'Regional Bank', 'Fintech Lender',
    'Solar Finance Company', 'Auto Finance Company', 'Mortgage Lender'
]

DEAL_STAGES = [
    'Lead In',
    'Qualification',
    'Discovery Call Scheduled',
    'Discovery Completed',
    'Demo Scheduled',
    'Demo Completed',
    'Proposal Sent',
    'Negotiation',
    'Closed Won',
    'Closed Lost'
]

LOSS_REASONS = [
    'No budget',
    'Timing not right',
    'Went with competitor',
    'No decision made',
    'Technical fit issues',
    'Price too high'
]

DEAL_SIZES = {
    'small': (25000, 50000),
    'medium': (50000, 150000),
    'large': (150000, 500000)
}

def generate_contacts(count=50):
    """Generate fake contacts/leads"""
    
    print(f"Generating {count} contacts...")
    
    contacts = []
    
    for i in range(count):
        # Mix of company types, but more credit unions for our ICP
        company_type = random.choices(
            COMPANY_TYPES,
            weights=[40, 20, 10, 10, 10, 5, 5]  # Weight toward credit unions
        )[0]
        
        # If it's a credit union, most have auto lending
        has_auto_lending = 'No'
        if 'Credit Union' in company_type:
            has_auto_lending = random.choice(['Yes', 'Yes', 'Yes', 'No'])  # 75% have auto
        elif 'Auto Finance' in company_type:
            has_auto_lending = 'Yes'  # Auto finance companies obviously have auto lending
        else:
            has_auto_lending = random.choice(['Yes', 'No', 'No'])  # 33% chance for others
        
        company_name = f"{fake.company()} {company_type}"
        
        contact = {
            'Contact_ID': f'CONT{10000 + i}',
            'Person_Name': fake.name(),
            'Email': fake.email(),
            'Phone': fake.phone_number(),
            'Job_Title': random.choice([
                'CFO', 'VP of Finance', 'Director of Finance',
                'Controller', 'Finance Manager', 'Treasury Manager',
                'COO', 'CEO', 'President', 'Chief Lending Officer',
                'VP of Lending', 'SVP of Lending', 'VP of Operations'
            ]),
            'Company_Name': company_name,
            'Company_Type': company_type,
            'Company_Size': random.choice(['1-50', '51-200', '201-1000', '1000+']),
            'Has_Auto_Lending': has_auto_lending,
            'Country': 'United States',
            'State': fake.state_abbr(),
            'City': fake.city(),
            'Source': random.choice([
                'LinkedIn', 'Website Form', 'Referral', 'Conference',
                'Cold Outreach', 'Inbound Demo Request', 'Partner'
            ]),
            'Created_Date': fake.date_between(start_date='-180d', end_date='today').strftime('%Y-%m-%d'),
        }
        
        contacts.append(contact)
    
    return contacts

def generate_deals(contacts, count=30):
    """Generate deals linked to contacts"""
    
    print(f"Generating {count} deals...")
    
    deals = []
    
    for i in range(count):
        contact = random.choice(contacts)
        
        # Deal stage determines other fields
        stage = random.choice(DEAL_STAGES)
        stage_index = DEAL_STAGES.index(stage)
        
        # Deal value based on company size
        if contact['Company_Size'] in ['1-50', '51-200']:
            deal_size = 'small'
        elif contact['Company_Size'] == '201-1000':
            deal_size = 'medium'
        else:
            deal_size = 'large'
        
        deal_value = random.randint(*DEAL_SIZES[deal_size])
        
        # Created date
        created_date = datetime.strptime(contact['Created_Date'], '%Y-%m-%d')
        deal_created = created_date + timedelta(days=random.randint(0, 30))
        
        # Expected close date
        if stage == 'Closed Won':
            expected_close = deal_created + timedelta(days=random.randint(30, 120))
            probability = 100
            status = 'won'
        elif stage == 'Closed Lost':
            expected_close = deal_created + timedelta(days=random.randint(30, 120))
            probability = 0
            status = 'lost'
        else:
            days_out = random.randint(7, 90)
            expected_close = datetime.now() + timedelta(days=days_out)
            # Probability increases with stage
            probability = min(10 + (stage_index * 10), 90)
            status = 'open'
        
        deal = {
            'Deal_ID': f'DEAL{20000 + i}',
            'Deal_Name': f"{contact['Company_Name']} - EnFi Platform",
            'Contact_ID': contact['Contact_ID'],
            'Contact_Name': contact['Person_Name'],
            'Company_Name': contact['Company_Name'],
            'Deal_Value': deal_value,
            'Currency': 'USD',
            'Stage': stage,
            'Status': status,
            'Probability': probability,
            'Expected_Close_Date': expected_close.strftime('%Y-%m-%d'),
            'Created_Date': deal_created.strftime('%Y-%m-%d'),
            'Days_In_Stage': (datetime.now().date() - deal_created.date()).days,
            'Source': contact['Source'],
            'Loss_Reason': random.choice(LOSS_REASONS) if stage == 'Closed Lost' else '',
            'Next_Step': generate_next_step(stage, status),
            'Last_Activity_Date': (datetime.now() - timedelta(days=random.randint(0, 14))).strftime('%Y-%m-%d'),
        }
        
        deals.append(deal)
    
    return deals

def generate_next_step(stage, status):
    """Generate realistic next steps based on stage"""
    
    if status in ['won', 'lost']:
        return ''
    
    next_steps = {
        'Lead In': 'Send intro email',
        'Qualification': 'Schedule discovery call',
        'Discovery Call Scheduled': 'Prepare discovery agenda',
        'Discovery Completed': 'Send demo invite',
        'Demo Scheduled': 'Prepare custom demo',
        'Demo Completed': 'Draft proposal',
        'Proposal Sent': 'Follow up on proposal questions',
        'Negotiation': 'Address pricing concerns',
    }
    
    return next_steps.get(stage, 'Follow up')

def generate_activities(deals, count=100):
    """Generate activities (calls, emails, meetings) for deals"""
    
    print(f"Generating {count} activities...")
    
    activities = []
    activity_types = ['Call', 'Email', 'Meeting', 'Demo', 'Follow-up', 'Proposal Review']
    
    for i in range(count):
        deal = random.choice([d for d in deals if d['Status'] == 'open'])
        
        activity_date = fake.date_between(start_date='-60d', end_date='today')
        
        # Generate realistic activity subjects
        activity_type = random.choice(activity_types)
        subjects = {
            'Call': f"Discovery call with {deal['Contact_Name']}",
            'Email': f"Sent pricing info to {deal['Contact_Name']}",
            'Meeting': f"Demo for {deal['Company_Name']}",
            'Demo': f"Product demo - {deal['Company_Name']}",
            'Follow-up': f"Check in with {deal['Contact_Name']}",
            'Proposal Review': f"Reviewed proposal with {deal['Company_Name']}"
        }
        
        activity = {
            'Activity_ID': f'ACT{30000 + i}',
            'Deal_ID': deal['Deal_ID'],
            'Contact_ID': deal['Contact_ID'],
            'Type': activity_type,
            'Subject': subjects[activity_type],
            'Date': activity_date.strftime('%Y-%m-%d'),
            'Duration_Minutes': random.choice([15, 30, 45, 60]) if activity_type in ['Call', 'Meeting', 'Demo'] else 0,
            'Outcome': random.choice(['Positive', 'Neutral', 'Needs Follow-up', 'Qualified', 'Not Qualified']),
            'Notes': generate_activity_note(activity_type, deal),
        }
        
        activities.append(activity)
    
    return activities

def generate_activity_note(activity_type, deal):
    """Generate realistic activity notes"""
    
    notes = {
        'Call': f"Discussed current manual processes. Managing ~{random.randint(1000, 10000)} loans. Pain points: reporting time, data quality issues.",
        'Email': f"Sent detailed pricing breakdown. Annual cost: ${deal['Deal_Value']:,}. Highlighted ROI of 6-9 months.",
        'Meeting': f"Strong interest in automation capabilities. Asked about integration with their core system.",
        'Demo': f"Showed end-to-end workflow. Very impressed with reporting features. CFO wants to see it.",
        'Follow-up': f"Checking status. Mentioned they're in budget planning cycle for Q{random.randint(1,4)}.",
        'Proposal Review': f"Walked through proposal. Questions about implementation timeline and support model."
    }
    
    return notes.get(activity_type, "Standard activity")

def upload_crm_data(contacts, deals, activities):
    """Upload all CRM data to S3"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder = 'crm-data'
    files_uploaded = []
    
    # Upload contacts
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=list(contacts[0].keys()))
    writer.writeheader()
    writer.writerows(contacts)
    
    contacts_file = f'{folder}/contacts_{timestamp}.csv'
    s3.put_object(Bucket=bucket_name, Key=contacts_file, Body=csv_buffer.getvalue())
    files_uploaded.append(contacts_file)
    
    # Upload deals
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=list(deals[0].keys()))
    writer.writeheader()
    writer.writerows(deals)
    
    deals_file = f'{folder}/deals_{timestamp}.csv'
    s3.put_object(Bucket=bucket_name, Key=deals_file, Body=csv_buffer.getvalue())
    files_uploaded.append(deals_file)
    
    # Upload activities
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=list(activities[0].keys()))
    writer.writeheader()
    writer.writerows(activities)
    
    activities_file = f'{folder}/activities_{timestamp}.csv'
    s3.put_object(Bucket=bucket_name, Key=activities_file, Body=csv_buffer.getvalue())
    files_uploaded.append(activities_file)
    
    return files_uploaded

def print_crm_summary(contacts, deals, activities):
    """Print CRM data summary"""
    
    # Deal metrics
    open_deals = [d for d in deals if d['Status'] == 'open']
    won_deals = [d for d in deals if d['Status'] == 'won']
    lost_deals = [d for d in deals if d['Status'] == 'lost']
    
    total_pipeline = sum(d['Deal_Value'] for d in open_deals)
    weighted_pipeline = sum(d['Deal_Value'] * d['Probability'] / 100 for d in open_deals)
    won_revenue = sum(d['Deal_Value'] for d in won_deals)
    
    print("\n" + "="*70)
    print("CRM DATA SUMMARY")
    print("="*70)
    print(f"Contacts: {len(contacts)}")
    print(f"Total Deals: {len(deals)}")
    print(f"  Open: {len(open_deals)}")
    print(f"  Won: {len(won_deals)}")
    print(f"  Lost: {len(lost_deals)}")
    print(f"\nPipeline Metrics:")
    print(f"  Total Pipeline Value: ${total_pipeline:,}")
    print(f"  Weighted Pipeline: ${weighted_pipeline:,.0f}")
    print(f"  Won Revenue: ${won_revenue:,}")
    print(f"  Win Rate: {len(won_deals)/(len(won_deals)+len(lost_deals))*100:.1f}%")
    print(f"\nActivities: {len(activities)}")
    print("="*70)

# Main execution
if __name__ == "__main__":
    print("\nPIPEDRIVE CRM DATA GENERATOR")
    print("="*70)
    
    # Get inputs
    num_contacts = input("How many contacts? (default: 50): ").strip()
    num_contacts = int(num_contacts) if num_contacts else 50
    
    num_deals = input("How many deals? (default: 30): ").strip()
    num_deals = int(num_deals) if num_deals else 30
    
    num_activities = input("How many activities? (default: 100): ").strip()
    num_activities = int(num_activities) if num_activities else 100
    
    # Generate data
    contacts = generate_contacts(num_contacts)
    deals = generate_deals(contacts, num_deals)
    activities = generate_activities(deals, num_activities)
    
    # Upload
    print("\nUploading to S3...")
    files = upload_crm_data(contacts, deals, activities)
    
    # Summary
    print_crm_summary(contacts, deals, activities)
    
    print(f"\n✓ Files uploaded:")
    for file in files:
        print(f"  s3://{bucket_name}/{file}")
    
    print("\nReady for AI agent analysis!")