# RFUZZ

Multi-domain path fuzzer with built-in anti-tarpit protection.

---

## Overview

RFUZZ is designed for one specific use case: scan hundreds of domains from bug bounty scopes against common sensitive paths in a single run, while avoiding classic traps that hang other scanners.

## Why use RFuZZ ? 

Other scanners work great for single-target enumeration. RFUZZ solves a different problem:
Scenario: You have a HackerOne program with 50+ in-scope domains. You want to check all of them for common sensitive files (.git/config, backup.zip, .env, config.php) in one go.
Problem: Traditional tools require looping through domains manually. If one domain has a tarpit (e.g., 1.5GB file served at 1 KB/s), the scanner hangs for hours.
Solution: RFUZZ processes all domains simultaneously and automatically skips traps, giving you results in minutes instead of hours.

---

## Key Features

### Trap Protection
Automatically skips requests that exhibit tarpit behavior:
- Responses larger than 5 MB (configurable)
- Download speeds below 5 KB/s
- Requests taking longer than 30 seconds

### Multi-Domain Scanning
Process entire HackerOne/Bugcrowd scopes in one command:
```
python rfuzz.py -d scope.txt -r sensitive_paths.txt
```


### Lightweight
Only two dependencies: `requests` and `urllib3`.

### Extensible
Simple Python codebase — easy to modify for custom workflows.

---

## Installation

```bash
pip install requests urllib3
```

## Usage

```
# Basic scan
python rfuzz.py -d scope.txt -r raft-small-files.txt -w 30 --max-size 10

# Aggressive mode (bypass weak WAFs)
python rfuzz.py -d targets.txt -r sensitive.txt -w 100 -t 5 --max-size 2 --max-time 10

# Custom 200/403/401 responses
python rfuzz.py -d domains.txt -r routes.txt --status-codes 200,403,401
```


## Command-line options
```
-d, --domains          Domains list file (required)
-r, --routes           Routes/paths list file (required)
-o, --output           Output file (default: results.txt)
-w, --workers          Number of threads (default: 20)
-t, --timeout          Request timeout in seconds (default: 8)
--max-size             Maximum response size in MB (default: 5)
--max-time             Maximum download time per request in seconds (default: 30)
--min-speed            Minimum acceptable download speed in KB/s (default: 5)
--follow-redirects     Follow HTTP redirects
--verify-ssl           Verify SSL certificates
--status-codes         Comma-separated status codes to report (default: 200,201,204,301,302,401,403,500)
--debug                Enable debug logging
```

## Disclaimer
For authorized testing only. Respect scope boundaries and rate limits.

# "RFuZZ. Find what others miss."
