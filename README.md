# Sales Toolkit: Weekend Project

## The Story

My fiancée got obsessed with Duolingo, so I downloaded Sololearn—basically Duolingo for Python. Been doing 10 minutes a day instead of scrolling Instagram. After a few months, I could *read* Python but couldn't *build* anything. That felt useless.

Last weekend I decided to actually make something. I work in financial services sales, so I know the pain: qualifying leads by hand takes forever, demo data is always generic, and nobody has time for manual CRM updates. I spent the weekend building tools to fix these problems. Started small—just wanted to generate fake loan data for demos. Then I thought the data should match each prospect. Then I built a CRM data generator for practice. Then I learned about Model Context Protocol and built an AI system that qualifies leads automatically. What should've taken 4 hours now takes 10 seconds. I had 50 contacts, it found 12 qualified leads and 2 perfect fits instantly. Turns out when you have a real problem to solve, you learn fast.

Built with Python, AWS S3, and Claude's MCP. Everything's configurable. Ready to use.

---

## What It Does

**Demo Data Generator** - Makes realistic loan portfolios (solar, auto, mortgage) in 30 seconds  
**Customer Scenario Builder** - Tailors demo data to each prospect's profile  
**CRM Data Generator** - Creates fake contacts/deals/activities for practice  
**AI Lead Qualification** - Scores leads against your ICP, ranks by fit, explains why

---

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/sales-toolkit.git
cd sales-toolkit
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
aws configure  # Enter your AWS credentials
python lead_qualification_server.py test
```

Update `bucket_name` in each script. See [SETUP.md](SETUP.md) for details.

---

## Tech

Python • AWS S3 • Claude MCP • boto3 • faker

---

*Built in a weekend.* ☕