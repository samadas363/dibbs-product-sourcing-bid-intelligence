# DIBBS Product Sourcing & Bid Intelligence System

A Python and PostgreSQL project for organizing and analyzing procurement index data from the Defense Logistics Agency's Internet Bid Board System (DIBBS).

## Project Overview

This project establishes a data-processing workflow for procurement records, with a focus on structured storage, identifier parsing, data-quality checks, and solicitation research.

The long-term objective is to support supplier sourcing, quotation comparison, deadline tracking, and bid-readiness analysis.

## Current Features

- Processes DIBBS index records from CSV and fixed-width text files.
- Parses solicitation-number candidates and material-number candidates.
- Stores procurement records in PostgreSQL.
- Uses database conflict handling to support repeat imports.
- Flags unusual material-number candidates for manual verification.
- Separates parsed candidates from identifiers verified against official solicitation documents.
- Stores verified solicitation and purchase-request line-item details.
- Supports database-backed search and reporting workflows.

## Project Audit

The current index audit processed 319 records and identified 300 distinct parsed solicitation candidates. Four records were flagged for additional review because their material-number candidates were nonnumeric.

One solicitation was checked against an official PDF, and two associated purchase-request line items were stored in the verified tables.

These figures describe the current working dataset, not the total number of active DIBBS opportunities.

## Technology Stack

- Python
- PostgreSQL
- SQL
- psycopg2
- python-dotenv
- CSV and fixed-width text processing

## Data Quality

Parsed values are treated as candidates until verified against official procurement documents. Records requiring further investigation remain flagged for review.

The project does not claim that all indexed opportunities are currently open or ready for bidding.

## Local Setup

1. Install Python and PostgreSQL.
2. Create a PostgreSQL database for the project.
3. Create a Python virtual environment.
4. Install dependencies from `requirements.txt`.
5. Configure a local `.env` file using `.env.example`.
6. Create the required tables using the project's SQL scripts.
7. Run the parser tests before importing records.

Never commit passwords, API keys, or other secrets.

## Project Status

Working prototype. Ongoing work includes identifier verification, data-quality improvements, and development of supplier sourcing and bid-readiness workflows.

## Disclaimer

This is an independent procurement data project and is not affiliated with or endorsed by the Defense Logistics Agency or the U.S. Department of Defense.
### DIBBS System Architecture

![DIBBS System Architecture](EXACT_FILENAME.png)

![DIBBS Python](dibbs%20python.PNG)

## Project Summary

![DIBBS Summary](dibbs%20summ.PNG)

## Industry Workflow

![DIBBS Industry Workflow](dibs%20indus.PNG)

