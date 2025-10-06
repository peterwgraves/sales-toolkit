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

# Asset class configurations
ASSET_CLASSES = {
    'solar': {
        'name': 'Solar Loan',
        'product_code': 'SLN',
        'loan_range': (15000, 75000),
        'term_options': [60, 84, 120, 180, 240],
        'rate_range': (3.99, 8.99),
        'collateral_field': 'Solar_System_Size_kW',
        'collateral_values': lambda: round(random.uniform(5.0, 15.0), 1),
        'additional_fields': {
            'Solar_Installer': lambda: random.choice(['SunRun', 'Tesla Energy', 'Vivint Solar', 'Sunpower', 'Trinity Solar']),
            'Estimated_Annual_Savings': lambda: round(random.uniform(800, 2500), 2)
        }
    },
    'auto': {
        'name': 'Auto Loan',
        'product_code': 'AUTO',
        'loan_range': (15000, 60000),
        'term_options': [36, 48, 60, 72, 84],
        'rate_range': (2.99, 7.99),
        'collateral_field': 'Vehicle_Year',
        'collateral_values': lambda: random.randint(2018, 2024),
        'additional_fields': {
            'Vehicle_Make': lambda: random.choice(['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Tesla', 'BMW']),
            'Vehicle_Model': lambda: random.choice(['Camry', 'Accord', 'F-150', 'Silverado', 'Model 3', 'X5']),
            'Vehicle_VIN': lambda: fake.bothify(text='??#############', letters='ABCDEFGHJKLMNPRSTUVWXYZ')
        }
    },
    'mortgage': {
        'name': 'Mortgage Loan',
        'product_code': 'MORT',
        'loan_range': (150000, 750000),
        'term_options': [180, 240, 360],
        'rate_range': (3.25, 7.50),
        'collateral_field': 'Property_Appraised_Value',
        'collateral_values': lambda: round(random.uniform(200000, 900000), 2),
        'additional_fields': {
            'Property_Type': lambda: random.choice(['Single Family', 'Condo', 'Townhouse', 'Multi-Family']),
            'Occupancy_Type': lambda: random.choice(['Primary Residence', 'Second Home', 'Investment'])
        }
    },
    'personal': {
        'name': 'Personal Loan',
        'product_code': 'PERS',
        'loan_range': (5000, 50000),
        'term_options': [24, 36, 48, 60],
        'rate_range': (5.99, 15.99),
        'collateral_field': 'Loan_Purpose',
        'collateral_values': lambda: random.choice(['Debt Consolidation', 'Home Improvement', 'Medical', 'Other']),
        'additional_fields': {
            'Secured_Unsecured': lambda: random.choice(['Unsecured', 'Secured']),
        }
    }
}

def generate_loan_portfolio(asset_class='solar', count=50):
    """Generate loan portfolio for any asset class
    
    Args:
        asset_class: Type of loan (solar, auto, mortgage, personal)
        count: Number of loans to generate
    """
    
    config = ASSET_CLASSES[asset_class]
    print(f"Generating {count} {config['name']} accounts...")
    
    loans = []
    
    for i in range(count):
        # Loan basics
        loan_amount = round(random.uniform(*config['loan_range']), 2)
        origination_date = fake.date_between(start_date='-3y', end_date='-6m')
        term_months = random.choice(config['term_options'])
        interest_rate = round(random.uniform(*config['rate_range']), 2)
        
        # Calculate payment
        monthly_rate = interest_rate / 100 / 12
        if monthly_rate > 0:
            monthly_payment = round(
                loan_amount * monthly_rate / (1 - (1 + monthly_rate)**(-term_months)),
                2
            )
        else:
            monthly_payment = round(loan_amount / term_months, 2)
        
        # Performance metrics
        days_since_origination = (datetime.now().date() - origination_date).days
        payments_made = min(int(days_since_origination / 30), term_months)
        principal_paid = round(monthly_payment * payments_made * 0.65, 2)
        current_balance = max(0, round(loan_amount - principal_paid, 2))
        
        # Delinquency status (weighted toward current)
        delinquency_status = random.choices(
            ['Current', '30DPD', '60DPD', '90DPD+'],
            weights=[87, 7, 4, 2]
        )[0]
        
        # Base loan data (common across all asset classes)
        loan = {
            # Core identifiers
            'Account_Number': f'{config["product_code"]}{100000 + i}',
            'Customer_ID': f'CUST{200000 + i}',
            'Product_Code': config['product_code'],
            'Product_Name': config['name'],
            
            # Dates
            'Origination_Date': origination_date.strftime('%Y-%m-%d'),
            'Maturity_Date': (origination_date + timedelta(days=term_months*30)).strftime('%Y-%m-%d'),
            'Last_Payment_Date': (datetime.now().date() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
            'Next_Payment_Due_Date': (datetime.now().date() + timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
            
            # Borrower details
            'Borrower_Name': fake.name(),
            'Credit_Score_At_Origination': random.randint(620, 820),
            'Current_Credit_Score': random.randint(620, 820),
            'Address': fake.street_address(),
            'City': fake.city(),
            'State': fake.state_abbr(),
            'Zip_Code': fake.zipcode(),
            
            # Financial details
            'Original_Principal_Amount': loan_amount,
            'Current_Principal_Balance': current_balance,
            'Interest_Rate_Percent': interest_rate,
            'Term_Months': term_months,
            'Monthly_Payment_Amount': monthly_payment,
            'Total_Payments_Made': payments_made,
            'Remaining_Payments': term_months - payments_made,
            
            # Performance metrics
            'Delinquency_Status': delinquency_status,
            'Days_Past_Due': 0 if delinquency_status == 'Current' else int(delinquency_status[:2]) if delinquency_status[:2].isdigit() else 90,
            'Total_Principal_Paid': principal_paid,
            'Total_Interest_Paid': round(monthly_payment * payments_made * 0.35, 2),
            'Last_Payment_Amount': monthly_payment if delinquency_status == 'Current' else round(random.uniform(0, monthly_payment), 2),
            
            # Administrative
            'Branch_Code': f'BR{random.randint(100, 999)}',
            'Loan_Officer_ID': f'LO{random.randint(1000, 9999)}',
            'Servicing_Status': random.choice(['Active', 'Active', 'Active', 'Paid Off', 'Charged Off']) if payments_made >= term_months else 'Active',
        }
        
        # Add asset-specific collateral field
        loan[config['collateral_field']] = config['collateral_values']()
        
        # Add additional asset-specific fields
        for field_name, field_generator in config['additional_fields'].items():
            loan[field_name] = field_generator()
        
        loans.append(loan)
    
    return loans

def upload_to_s3(loans, asset_class, folder='demo-data'):
    """Upload loan data to S3"""
    
    # Create CSV
    csv_buffer = StringIO()
    fieldnames = list(loans[0].keys())
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(loans)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f'{folder}/{asset_class}_loans_{timestamp}.csv'
    
    # Upload
    s3.put_object(
        Bucket=bucket_name,
        Key=file_name,
        Body=csv_buffer.getvalue()
    )
    
    return file_name

def print_portfolio_summary(loans, asset_class):
    """Print portfolio analytics"""
    config = ASSET_CLASSES[asset_class]
    
    total_balance = sum(loan['Current_Principal_Balance'] for loan in loans)
    total_originated = sum(loan['Original_Principal_Amount'] for loan in loans)
    avg_credit_score = sum(loan['Current_Credit_Score'] for loan in loans) / len(loans)
    
    status_counts = {}
    for loan in loans:
        status = loan['Delinquency_Status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    avg_rate = sum(loan['Interest_Rate_Percent'] for loan in loans) / len(loans)
    
    print("\n" + "="*70)
    print(f"{config['name'].upper()} PORTFOLIO SUMMARY")
    print("="*70)
    print(f"Portfolio Size: {len(loans)} loans")
    print(f"Total Outstanding Balance: ${total_balance:,.2f}")
    print(f"Total Originated Amount: ${total_originated:,.2f}")
    print(f"Average Interest Rate: {avg_rate:.2f}%")
    print(f"Average Credit Score: {avg_credit_score:.0f}")
    print(f"\nPerformance by Status:")
    for status, count in sorted(status_counts.items()):
        pct = count / len(loans) * 100
        print(f"  {status}: {count} ({pct:.1f}%)")
    print("="*70)

# Main execution
if __name__ == "__main__":
    print("LOAN PORTFOLIO GENERATOR")
    print("="*70)
    print("Available asset classes:")
    for key, config in ASSET_CLASSES.items():
        print(f"  {key}: {config['name']}")
    print()
    
    # Get user input
    asset_class = input("Enter asset class (default: solar): ").strip().lower()
    if not asset_class or asset_class not in ASSET_CLASSES:
        asset_class = 'solar'
    
    count = input("How many loans to generate? (default: 100): ").strip()
    count = int(count) if count else 100
    
    # Generate portfolio
    loans = generate_loan_portfolio(asset_class=asset_class, count=count)
    
    # Upload to S3
    file_path = upload_to_s3(loans, asset_class)
    
    # Show summary
    print_portfolio_summary(loans, asset_class)
    print(f"\n✓ Portfolio uploaded to: s3://{bucket_name}/{file_path}")
    print("\nReady for demos!")