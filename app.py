#!/usr/bin/env python3
import os
import sys
import csv
import argparse
import subprocess
import json
from pathlib import Path

def check_docker():
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Docker is not installed. Please install Docker first.")
        sys.exit(1)

def extract_emails(domain_file):
    results = {}

    with open(domain_file, 'r') as f:
        domains = [line.strip() for line in f if line.strip()]

    for domain in domains:
        print(f"\nProcessing domain: {domain}")
        try:
            # Run BBOT using Docker with a timeout of 300 seconds (5 minutes)
            cmd = [
                "docker", "run", "--rm",
                "blacklanternsecurity/bbot:stable",
                "-t", domain,
                "-f", "email-enum",
                "-o", "json"
            ]

            output = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Create temporary file to store output
            temp_file = f"temp_{domain}.txt"
            with open(temp_file, 'w') as f:
                f.write(output.stdout)

            # Extract emails using grep
            try:
                grep_cmd = ["grep", "-oE", r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', temp_file]
                emails = subprocess.run(
                    grep_cmd,
                    capture_output=True,
                    text=True
                ).stdout.strip().split('\n')

                # Filter out empty strings and deduplicate emails
                emails = list(set(filter(None, emails)))

                if emails:
                    # Only keep emails that match the domain
                    domain_emails = [email for email in emails if domain in email]
                    if domain_emails:
                        results[domain] = domain_emails
                        print(f"Found {len(domain_emails)} email(s) for {domain}")
                    else:
                        print(f"No matching emails found for {domain}")
                        results[domain] = []
                else:
                    print(f"No emails found for {domain}")
                    results[domain] = []

            except subprocess.CalledProcessError:
                print(f"No emails found for {domain}")
                results[domain] = []

            # Clean up temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)

        except subprocess.TimeoutExpired:
            print(f"Timeout while processing {domain}")
            results[domain] = []
        except subprocess.CalledProcessError as e:
            print(f"Error processing {domain}: {e}")
            results[domain] = []
        except Exception as e:
            print(f"Unexpected error processing {domain}: {e}")
            results[domain] = []

        # Add a small delay between domains to prevent rate limiting
        subprocess.run(["sleep", "2"])

    return results

def save_to_csv(results, output_file="email_results.csv"):
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Domain", "Emails"])

        for domain, emails in results.items():
            writer.writerow([domain, ", ".join(emails)])

    print(f"\nResults saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Email extraction tool using BBOT")
    parser.add_argument("-p", "--path", required=True, help="Path to file containing domain list")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: File {args.path} does not exist")
        sys.exit(1)

    print("Checking Docker installation...")
    check_docker()

    print("\nStarting email extraction...")
    results = extract_emails(args.path)

    save_to_csv(results)

if __name__ == "__main__":
    main()
