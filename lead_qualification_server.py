#!/usr/bin/env python3
"""
Lead Qualification MCP Server for EnFi
Scores leads against ICP: Credit Unions in US with indirect auto lending
"""

import asyncio
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import boto3
import csv
from io import StringIO
from datetime import datetime

# ============================================================================
# AWS & ICP CONFIGURATION
# ============================================================================

s3 = boto3.client('s3')
bucket_name = 'enfi-sales-toolkit-xyz123'

SCORING = {
    'company_type': 35,
    'has_auto_lending': 35,
    'company_size': 10,
    'title': 10,
    'source': 5,
    'state': 5,
}

ICP_CONFIG = {
    'name': 'EnFi Primary ICP',
    'description': 'Credit unions in the United States with indirect auto lending business',
    'required': {
        'company_type': ['Credit Union'],
        'country': ['United States'],
        'has_auto_lending': True,
    },
    'preferred': {
        'company_size': ['201-1000', '1000+'],
        'titles': ['CFO', 'VP of Finance', 'COO', 'CEO', 
                   'Chief Lending Officer', 'VP of Lending', 'SVP of Lending'],
        'sources': ['Referral', 'Inbound Demo Request', 'Conference'],
        'states': [],
    }
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def read_contacts_from_s3():
    """Read the latest contacts CSV from S3"""
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix='crm-data/contacts_')
        
        if 'Contents' not in response:
            return None, "No contact data found in S3"
        
        files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
        latest = files[0]
        
        obj = s3.get_object(Bucket=bucket_name, Key=latest['Key'])
        csv_content = obj['Body'].read().decode('utf-8')
        contacts = list(csv.DictReader(StringIO(csv_content)))
        
        return contacts, None
    
    except Exception as e:
        return None, f"Error reading contacts: {str(e)}"

def score_lead(contact):
    """Score a single lead against ICP criteria"""
    
    score = 0
    max_score = sum(SCORING.values())
    reasons = []
    gaps = []
    disqualified = False
    
    # Company Type (35 points)
    company_type = contact.get('Company_Type', '')
    if company_type in ICP_CONFIG['required']['company_type']:
        score += SCORING['company_type']
        reasons.append(f"✓ Perfect fit: {company_type}")
    else:
        gaps.append(f"✗ NOT A CREDIT UNION: {company_type}")
        disqualified = True
    
    # Auto Lending (35 points)
    has_auto = contact.get('Has_Auto_Lending', 'No') == 'Yes'
    if has_auto:
        score += SCORING['has_auto_lending']
        reasons.append(f"✓ Has indirect auto lending")
    else:
        gaps.append(f"✗ NO AUTO LENDING BUSINESS")
        disqualified = True
    
    # Company Size (10 points)
    company_size = contact.get('Company_Size', '')
    if company_size in ICP_CONFIG['preferred']['company_size']:
        score += SCORING['company_size']
        reasons.append(f"✓ Good size: {company_size} employees")
    else:
        reasons.append(f"• Size: {company_size} employees")
    
    # Title (10 points)
    title = contact.get('Job_Title', '')
    if title in ICP_CONFIG['preferred']['titles']:
        score += SCORING['title']
        reasons.append(f"✓ Decision maker: {title}")
    else:
        reasons.append(f"• Title: {title}")
    
    # Source (5 points)
    source = contact.get('Source', '')
    if source in ICP_CONFIG['preferred']['sources']:
        score += SCORING['source']
        reasons.append(f"✓ High-intent: {source}")
    else:
        reasons.append(f"• Source: {source}")
    
    # Geography (5 points)
    state = contact.get('State', '')
    priority_states = ICP_CONFIG['preferred']['states']
    if not priority_states or state in priority_states:
        score += SCORING['state']
        reasons.append(f"✓ Location: {state}")
    
    # Calculate final score
    if disqualified:
        score_pct = 0
        tier = "DISQUALIFIED"
        priority = "❌"
    else:
        score_pct = round((score / max_score) * 100, 1)
        if score_pct >= 90:
            tier = "A - Excellent"
            priority = "🔥"
        elif score_pct >= 80:
            tier = "B - Strong"
            priority = "✅"
        elif score_pct >= 70:
            tier = "C - Qualified"
            priority = "⚠️"
        else:
            tier = "D - Weak"
            priority = "🤔"
    
    return {
        'contact_id': contact.get('Contact_ID'),
        'name': contact.get('Person_Name'),
        'company': contact.get('Company_Name'),
        'company_type': company_type,
        'title': title,
        'email': contact.get('Email'),
        'phone': contact.get('Phone'),
        'state': state,
        'source': source,
        'created': contact.get('Created_Date'),
        'score': score,
        'score_pct': score_pct,
        'tier': tier,
        'priority': priority,
        'reasons': reasons,
        'gaps': gaps,
        'disqualified': disqualified,
    }

# ============================================================================
# MCP SERVER
# ============================================================================

app = Server("lead-qualification-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="score_all_leads",
            description="Score all leads against EnFi's ICP",
            inputSchema={
                "type": "object",
                "properties": {
                    "qualified_only": {
                        "type": "boolean",
                        "description": "Show only qualified leads",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="get_priority_list",
            description="Get top priority leads for outreach",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "number",
                        "description": "Number of leads",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="view_icp",
            description="View current ICP criteria",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    
    if name == "score_all_leads":
        contacts, error = read_contacts_from_s3()
        if error:
            return [TextContent(type="text", text=f"❌ {error}")]
        
        scored = [score_lead(c) for c in contacts]
        
        if arguments.get('qualified_only', True):
            scored = [s for s in scored if not s['disqualified']]
        
        scored.sort(key=lambda x: x['score_pct'], reverse=True)
        
        output = f"# Lead Scoring Results\n\n"
        output += f"**Total Analyzed:** {len(contacts)}\n"
        output += f"**Qualified:** {len(scored)}\n\n"
        
        for lead in scored[:20]:  # Top 20
            output += f"## {lead['priority']} {lead['name']} ({lead['score_pct']}%)\n"
            output += f"**{lead['title']}** at **{lead['company']}**\n"
            output += f"📧 {lead['email']} | 📱 {lead['phone']} | 📍 {lead['state']}\n\n"
            for r in lead['reasons'][:3]:
                output += f"- {r}\n"
            output += "\n---\n\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "get_priority_list":
        contacts, error = read_contacts_from_s3()
        if error:
            return [TextContent(type="text", text=f"❌ {error}")]
        
        scored = [score_lead(c) for c in contacts if not score_lead(c)['disqualified']]
        scored.sort(key=lambda x: x['score_pct'], reverse=True)
        
        count = int(arguments.get('count', 10))
        top = scored[:count]
        
        output = f"# 🎯 Top {count} Priority Leads\n\n"
        for i, lead in enumerate(top, 1):
            output += f"## {i}. {lead['name']} ({lead['score_pct']}%)\n"
            output += f"**{lead['title']}** at **{lead['company']}**\n"
            output += f"📧 {lead['email']}\n📱 {lead['phone']}\n📍 {lead['state']}\n\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "view_icp":
        output = f"# {ICP_CONFIG['name']}\n\n"
        output += f"*{ICP_CONFIG['description']}*\n\n"
        output += "## Required:\n"
        output += f"- Company Type: Credit Union\n"
        output += f"- Has Auto Lending: Yes\n\n"
        output += "## Preferred:\n"
        output += f"- Size: 201+ employees\n"
        output += f"- Titles: CFO, VP Finance, COO, Lending Officers\n"
        
        return [TextContent(type="text", text=output)]

async def run_server():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

# ============================================================================
# MAIN
# ============================================================================

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        print("=== TEST MODE ===\n")
        contacts, error = read_contacts_from_s3()
        
        if error:
            print(f"❌ {error}")
            return
        
        print(f"✓ Loaded {len(contacts)} contacts\n")
        
        scored = [score_lead(c) for c in contacts]
        qualified = [s for s in scored if not s['disqualified']]
        qualified.sort(key=lambda x: x['score_pct'], reverse=True)
        
        print(f"✓ {len(qualified)} qualified leads\n")
        print("🎯 Top 5:\n")
        
        for i, lead in enumerate(qualified[:5], 1):
            print(f"{i}. {lead['priority']} {lead['name']} - {lead['score_pct']}%")
            print(f"   {lead['title']} at {lead['company']}")
            print(f"   {lead['email']}\n")
    
    else:
        # MCP server mode
        asyncio.run(run_server())

if __name__ == "__main__":
    main()