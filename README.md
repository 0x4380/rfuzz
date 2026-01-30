=
                            R F U Z Z   v1.1
          Multi-Domain Path/Files Fuzzer for Security Researches
================================================================================

[!] QUICK START
    pip install requests urllib3
    python rfuzz.py -d domains.txt -r routes.txt -w 30

[!] WHAT IT DOES
    • Blasts multiple domains with common paths/sensitive files
    • Finds 200/403/401 responses FAST
    • Built-in trap protection (slow downloads, huge files)
    • Colorized output + detailed reporting

[!] WHY USE IT
    HackerOne scope got 50 domains? 
    Run once. get all /.git/config, /backup.zip, /admin.php in 60 sec.
    No more manual dirbusting per domain.

[!] TRAP PROTECTION (anti-tarpit)
    • Max response size: 5 MB (configurable)
    • Max download time: 30 sec per request
    • Min speed check: 5 KB/s (skips nginx rate-limit traps)
    • Streaming downloads (no memory bombs)

[!] USAGE
    python rfuzz.py -d domains.txt -r routes.txt [OPTIONS]

    -d, --domains      domains list (scope from HackerOne/Bugcrowd)
    -r, --routes       paths list (.git/config, .env, backup.zip etc)
    -w, --workers      threads (default: 20)
    -t, --timeout      request timeout (default: 8 sec)
    --max-size         max response size in MB (default: 5)
    --max-time         max download time per request (default: 30 sec)
    --status-codes     custom status codes (default: 200,403,401,301,302,500)

[!] EXAMPLES
    # Basic scan
    python rfuzz.py -d scope.txt -r raft-small-files.txt -w 50

    # Aggressive mode (bypass weak WAFs)
    python rfuzz.py -d targets.txt -r sensitive.txt -w 100 -t 5 \
                    --max-size 2 --max-time 10

    # Only 200/403 responses
    python rfuzz.py -d domains.txt -r routes.txt --status-codes 200,403

[!] REQUIREMENTS
    pip install requests urllib3

[!] OUTPUT
    results.txt    → grouped by status codes + skipped traps
    scanner.log    → debug log (enable with --debug)

[!] DISCLAIMER
    For authorized testing ONLY.
    Respect scope boundaries. Don't be that guy.

=
                      "RFuZZ. Find what others miss."
================================================================================
