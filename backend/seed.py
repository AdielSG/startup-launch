"""
seed.py — populate the database with 3 fake companies for local testing.

Run from the backend/ directory:
    python seed.py

Drops and recreates all tables on every run so stale null data never persists.
The 3 companies cover both performance outcomes (threshold X=500, LI=100):
  - Mintlify → Strong       (X: 1200, LI: 180 — both above threshold)
  - Resend   → Poor         (X:   95, LI:  30 — both below threshold)
  - Unkey    → Poor         (X:  340, LI:  85 — both below threshold)
"""

from datetime import date

from database import Base, SessionLocal, engine
from models import AppSettings, Company, Contact, FundingRound, LaunchPost

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_DATA = [
    {
        "company": {
            "name": "Mintlify",
            "domain": "mintlify.com",
            "description": (
                "API documentation that looks great out of the box. "
                "Write docs with MDX, deploy with one click."
            ),
            "founded_year": 2022,
            "yc_batch": "W22",
        },
        "funding_rounds": [
            {
                "amount": 1_800_000,
                "round_type": "seed",
                "date": date(2022, 1, 15),
                "source": "crunchbase",
            },
        ],
        "launch_posts": [
            {
                "platform": "twitter",
                "post_url": "https://twitter.com/mintlify/status/1000000001",
                "likes": 1200,
                "reposts": 210,
                "date": date(2022, 2, 3),
            },
            {
                "platform": "hackernews",
                "post_url": "https://news.ycombinator.com/item?id=30000001",
                "likes": 312,
                "reposts": None,
                "date": date(2022, 2, 3),
            },
            {
                "platform": "linkedin",
                "post_url": "https://www.linkedin.com/posts/mintlify_seed-launch-activity-1000000001",
                "likes": 180,
                "reposts": 42,
                "date": date(2022, 2, 3),
            },
        ],
        "contact": {
            "email": "founders@mintlify.com",
            "phone": None,
            "linkedin_url": "https://linkedin.com/company/mintlify",
            "x_handle": "mintlify",
        },
    },
    {
        "company": {
            "name": "Resend",
            "domain": "resend.com",
            "description": (
                "Email API for developers. "
                "Build, test, and deliver transactional emails at scale."
            ),
            "founded_year": 2023,
            "yc_batch": "W23",
        },
        "funding_rounds": [
            {
                "amount": 3_000_000,
                "round_type": "seed",
                "date": date(2023, 2, 7),
                "source": "crunchbase",
            },
        ],
        "launch_posts": [
            {
                "platform": "twitter",
                "post_url": "https://twitter.com/resendlabs/status/1000000002",
                "likes": 95,    # POOR — below threshold of 500
                "reposts": 14,
                "date": date(2023, 3, 12),
            },
            {
                "platform": "hackernews",
                "post_url": "https://news.ycombinator.com/item?id=30000002",
                "likes": 89,
                "reposts": None,
                "date": date(2023, 3, 12),
            },
            {
                "platform": "linkedin",
                "post_url": "https://www.linkedin.com/posts/resend_email-developer-activity-1000000002",
                "likes": 30,    # POOR — below threshold of 100
                "reposts": 8,
                "date": date(2023, 3, 12),
            },
        ],
        "contact": {
            "email": "hello@resend.com",
            "phone": None,
            "linkedin_url": "https://linkedin.com/company/resend",
            "x_handle": "resendlabs",
        },
    },
    {
        "company": {
            "name": "Unkey",
            "domain": "unkey.dev",
            "description": (
                "Open source API authentication and authorization. "
                "Add API keys to your product in minutes."
            ),
            "founded_year": 2023,
            "yc_batch": None,
        },
        "funding_rounds": [
            {
                "amount": 600_000,
                "round_type": "pre_seed",
                "date": date(2023, 8, 22),
                "source": "crunchbase",
            },
        ],
        "launch_posts": [
            {
                "platform": "twitter",
                "post_url": "https://twitter.com/unkeyhq/status/1000000003",
                "likes": 340,   # POOR — below threshold of 500
                "reposts": 67,
                "date": date(2023, 9, 5),
            },
            {
                "platform": "hackernews",
                "post_url": "https://news.ycombinator.com/item?id=30000003",
                "likes": 201,
                "reposts": None,
                "date": date(2023, 9, 5),
            },
            {
                "platform": "linkedin",
                "post_url": "https://www.linkedin.com/posts/unkey_api-auth-activity-1000000003",
                "likes": 85,    # POOR — below threshold of 100
                "reposts": 21,
                "date": date(2023, 9, 5),
            },
        ],
        "contact": {
            "email": "andreas@unkey.dev",
            "phone": None,
            "linkedin_url": "https://linkedin.com/company/unkey",
            "x_handle": "unkeyhq",
        },
    },
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def seed():
    print("Startup Launch Dashboard — seed script")
    print("=" * 40)

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating all tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Ensure default settings row exists
        if not db.query(AppSettings).first():
            db.add(AppSettings())
            db.commit()
            print("  + AppSettings defaults created (X threshold: 200, LI threshold: 50)")

        inserted = 0
        skipped = 0

        for entry in SEED_DATA:
            name = entry["company"]["name"]

            if db.query(Company).filter(Company.name == name).first():
                print(f"  ~ {name} already exists, skipping")
                skipped += 1
                continue

            # Insert company
            company = Company(**entry["company"])
            db.add(company)
            db.flush()  # populate company.id before inserting child rows

            # Insert related rows
            for fr in entry["funding_rounds"]:
                db.add(FundingRound(company_id=company.id, **fr))

            for lp in entry["launch_posts"]:
                db.add(LaunchPost(company_id=company.id, **lp))

            db.add(Contact(company_id=company.id, **entry["contact"]))

            db.commit()
            db.refresh(company)

            total_funding = sum(
                fr["amount"] for fr in entry["funding_rounds"] if fr["amount"]
            )
            twitter_post = next(
                (lp for lp in entry["launch_posts"] if lp["platform"] == "twitter"), None
            )
            twitter_likes = twitter_post["likes"] if twitter_post else None
            performance = (
                "POOR" if twitter_likes is not None and twitter_likes < 500 else "Strong"
            )

            print(
                f"  + {name:<12} "
                f"funding=${total_funding / 1e6:.1f}M  "
                f"twitter_likes={twitter_likes}  "
                f"[{performance}]"
            )
            inserted += 1

        print()
        print(f"Done. {inserted} inserted, {skipped} skipped.")
        print()
        print("Start the backend and visit http://localhost:8000/launches/ to verify.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
