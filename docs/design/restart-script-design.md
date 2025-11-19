# Server Restart Script Architecture Specification

## Executive Summary

This document specifies the architectural design for a clean, production-ready server restart script that manages both FastAPI (backend) and Next.js (frontend) services. The script handles concurrent service startup, health verification, graceful shutdown, and comprehensive error reporting.

---

## 1. Script Structure & Execution Flow

### 1.1 Overall Architecture

```
Script Entry Point
    ↓
[A] Pre-flight Validation
    ├─ Check script prerequisites
    ├─ Validate directory structure
    ├─ Verify port availability
    └─ Setup logging infrastructure
    ↓
[B] Clean Shutdown Phase
    ├─ Identify processes on ports 3000 & 8000
    ├─ Graceful termination (SIGTERM, then SIGKILL)
    ├─ Verify process removal
    └─ Clean up lock files
    ↓
[C] Service Startup Phase
    ├─ Backend: Activate venv + start uvicorn
    ├─ Frontend: Navigate to directory + npm run dev
    ├─ Capture PIDs for tracking
    └─ Redirect output to log files
    ↓
[D] Initialization Delay
    ├─ Backend: 3-5 second warm-up
    ├─ Frontend: 5-8 second build phase
    └─ Progressive retry window
    ↓
[E] Concurrent Health Checks
    ├─ Backend health: GET http://localhost:8000/health
    ├─ Frontend health: HTTP response from http://localhost:3000
    ├─ Timeout: 30-60 seconds with exponential backoff
    └─ Parallel execution for efficiency
    ↓
[F] Status Reporting
    ├─ Summary of both services
    ├─ Port binding verification
    ├─ Log file locations
    └─ Next steps for user
    ↓
[G] Exit with Status Code
    ├─ 0: Both services healthy
    ├─ 1: Shutdown failed
    ├─ 2: Backend startup/health failed
    ├─ 3: Frontend startup/health failed
    ├─ 4: Mixed failures or fatal errors
```

### 1.2 Process Execution Model

**Startup Strategy:**
- **Backend**: Synchronous activation (blocking) with immediate background PID capture
- **Frontend**: Synchronous activation (blocking) with immediate background PID capture
- **Parallelization Point**: Health checks run concurrently against both services

**Log Strategy:**
- Backend STDOUT/STDERR → `logs/backend.log` with timestamp
- Frontend STDOUT/STDERR → `logs/frontend.log` with timestamp
- Main script output → STDOUT with structured formatting

---

## 2. Error Handling Architecture

### 2.1 Error Categories & Response Strategy

```
ERROR CLASS A: Cleanup/Shutdown Failures
├─ Cannot identify process on port 3000
├─ Cannot identify process on port 8000
├─ Cannot kill process (permission denied)
├─ Process still present after timeout
├─ HANDLER: Warn user, offer manual intervention, continue to startup
├─ IMPACT: May prevent clean startup if port occupied
└─ EXIT CODE: 1 (if critical), continue with 5-second delay (if recoverable)

ERROR CLASS B: Backend Startup Failures
├─ Virtual environment not found
├─ Python dependencies missing
├─ Cannot activate venv
├─ Uvicorn process exits immediately
├─ Port 8000 still occupied after cleanup
├─ HANDLER: Check logs, verify venv setup, offer manual troubleshooting
├─ IMPACT: Backend unavailable, frontend can still start
└─ EXIT CODE: 2 (if fails health check)

ERROR CLASS C: Frontend Startup Failures
├─ Directory not accessible
├─ Node modules not installed
├─ npm command not found
├─ Next.js build fails
├─ Port 3000 still occupied after cleanup
├─ HANDLER: Check logs, verify node setup, offer manual rebuild
├─ IMPACT: Frontend unavailable, backend can still operate
└─ EXIT CODE: 3 (if fails health check)

ERROR CLASS D: Health Check Failures
├─ Backend responds with non-200 after timeout
├─ Frontend doesn't respond after timeout
├─ Service exits during health check
├─ Network connectivity issues
├─ HANDLER: Extended retry loop with exponential backoff
├─ IMPACT: Services may still be initializing, offer retry option
└─ EXIT CODE: 2 or 3 (depending on service)

ERROR CLASS E: Fatal/Unrecoverable
├─ Cannot create log directory
├─ Port already in use (unknown process)
├─ Insufficient disk space
├─ System resource constraints
├─ HANDLER: Abort immediately with clear error message
├─ IMPACT: Script cannot proceed
└─ EXIT CODE: 4
```

### 2.2 Shutdown Error Recovery Paths

```
Scenario: Process running on port 8000, cannot be killed

Flow:
    Check for PID on port 8000
        ↓
    Send SIGTERM (-15) with 5-second wait
        ↓
    Process still exists?
        ├─ YES → Send SIGKILL (-9)
        │   ├─ SUCCESS → Continue to startup
        │   └─ FAIL → Offer manual options:
        │       ├─ Retry (with longer timeout)
        │       ├─ Manual kill with sudo
        │       └─ Abort script
        └─ NO → Continue to startup
```

### 2.3 Health Check Retry Strategy

```
Initial Delay: 5 seconds (allows service initialization)

Retry Loop (max 12 attempts over 60 seconds):
    Attempt 1: Immediate
    Attempt 2: +2 seconds
    Attempt 3: +3 seconds
    Attempt 4: +4 seconds (exponential backoff)
    Attempt 5+: +5 seconds (plateau)

    Total time: ~60 seconds maximum

Timeout per attempt: 3 seconds (HTTP connection + response)

Success Conditions:
    Backend: HTTP 200 from /health endpoint
    Frontend: HTTP 200 from root endpoint

If all attempts fail:
    → Report failure
    → Direct user to logs
    → Suggest manual startup
```

---

## 3. Health Check Strategy

### 3.1 Backend Health Check

**Endpoint:** `http://localhost:8000/health`

**Request Specifications:**
- Method: GET
- Timeout: 3 seconds
- Accept codes: 200
- Expected response: `{"status": "healthy"}`
- Fallback check: Port 8000 responds to any HTTP

**Detection Method:**
```
Primary: curl -s -m 3 http://localhost:8000/health
Fallback: curl -s -m 3 http://localhost:8000/ (root endpoint exists)
Port verification: lsof -i :8000 | grep uvicorn
```

**Success Indicators:**
- HTTP 200 status code
- Response time < 3 seconds
- Port listening with uvicorn process
- Process not in zombie state

**Failure Indicators:**
- Connection refused
- HTTP 500 or other error codes
- Timeout exceeded
- Process exits

### 3.2 Frontend Health Check

**Endpoint:** `http://localhost:3000`

**Request Specifications:**
- Method: GET
- Timeout: 5 seconds (Next.js build may take longer)
- Accept codes: 200, 404 (404 from Next.js acceptable if server responds)
- Expected response: HTML page or redirect

**Detection Method:**
```
Primary: curl -s -m 5 -I http://localhost:3000
Fallback: curl -s -m 5 http://localhost:3000 (check for meaningful response)
Port verification: lsof -i :3000 | grep node
```

**Success Indicators:**
- HTTP response received (200, 301, 302, 404 acceptable)
- Server listening on port 3000
- Node process active
- Response within 5 seconds

**Failure Indicators:**
- Connection refused
- Timeout exceeded
- Port not listening
- Process exits

### 3.3 Concurrent Health Check Execution

```
Health Check Coordinator
    ↓
    Launch Backend Check (background, 60s timeout)
    ↓
    Launch Frontend Check (background, 60s timeout)
    ↓
    Monitor both in parallel
    ↓
    Report results when both complete or timeout

Exit Conditions:
    ├─ Both healthy → Success (exit 0)
    ├─ Backend healthy, Frontend failed → Partial (exit 3)
    ├─ Frontend healthy, Backend failed → Partial (exit 2)
    └─ Both failed → Failure (exit 4)
```

---

## 4. Log Management Approach

### 4.1 Log Directory Structure

```
Project Root/
├── logs/
│   ├── backend.log          (uvicorn output + stderr)
│   ├── frontend.log         (npm dev output + stderr)
│   ├── restart.log          (script execution log)
│   └── .gitkeep             (ensure logs/ exists in git)
```

### 4.2 Log Content Strategy

**Backend Log (`logs/backend.log`):**
```
Format: [TIMESTAMP] [LEVEL] MESSAGE
Content:
    - Uvicorn startup sequence
    - Port binding confirmation
    - ASGI application initialization
    - Request logs (if enabled)
    - Error traces
    - Shutdown sequence

Rotation: Overwrite on each restart (capture current session only)
Retention: 1 session (5-10 minutes typical)
```

**Frontend Log (`logs/frontend.log`):**
```
Format: [TIMESTAMP] MESSAGE
Content:
    - npm dev initialization
    - Next.js compilation output
    - Module resolution
    - Port binding confirmation
    - Build warnings/errors
    - Shutdown sequence

Rotation: Overwrite on each restart
Retention: 1 session (5-30 seconds typical)
```

**Restart Log (`logs/restart.log`):**
```
Format: [TIMESTAMP] [SECTION] MESSAGE
Content:
    - Script execution phases
    - Process identification
    - Shutdown operations
    - Startup operations
    - Health check attempts
    - Final status report
    - Timing information

Example:
    [2025-11-19 14:35:22] [PRE-FLIGHT] Validating script prerequisites...
    [2025-11-19 14:35:22] [PRE-FLIGHT] Using project root: /path/to/project
    [2025-11-19 14:35:23] [SHUTDOWN] Found process 1234 on port 8000
    [2025-11-19 14:35:23] [SHUTDOWN] Sending SIGTERM to process 1234
    [2025-11-19 14:35:28] [SHUTDOWN] Port 8000 verified free
    [2025-11-19 14:35:28] [STARTUP] Starting backend service...
    [2025-11-19 14:35:30] [HEALTH-CHECK] Backend: Checking http://localhost:8000/health
    [2025-11-19 14:35:31] [HEALTH-CHECK] Backend: Healthy (response time: 45ms)
    [2025-11-19 14:35:35] [HEALTH-CHECK] Frontend: Healthy (response time: 234ms)
    [2025-11-19 14:35:35] [STATUS] Services started successfully
```

### 4.3 Log Output Redirection

**Backend Capture:**
```
Command: uvicorn app.main:app ... > logs/backend.log 2>&1 &
          ↓
Results in: STDOUT + STDERR combined in single file
Timestamp: Added by Python logging (if configured) or not (raw output)
```

**Frontend Capture:**
```
Command: npm run dev > logs/frontend.log 2>&1 &
          ↓
Results in: STDOUT + STDERR combined in single file
Timestamp: npm adds timestamps automatically
```

**Script Logging:**
```
Pattern: Log each phase to STDOUT + logs/restart.log
Example: printf "[$(date '+%Y-%m-%d %H:%M:%S')] [SHUTDOWN] Message\n" >> logs/restart.log
Dual output: User sees progress, file has full record
```

### 4.4 Log Cleanup Strategy

```
On script start:
    - Create logs/ directory if missing
    - Truncate restart.log (start fresh)
    - Note: Keep backend.log and frontend.log for current session troubleshooting

On script completion:
    - Leave all logs for user inspection
    - Offer summary: "See logs/backend.log for details"

Manual cleanup:
    - User responsibility: rm logs/*.log (or add --clean-logs flag)
    - Only clean on explicit request (non-destructive default)
```

---

## 5. Port Management & Verification

### 5.1 Port Detection Strategy

```
Port 3000 (Frontend):
    Command: lsof -i :3000 2>/dev/null | grep -E "node|npm"
    Result: PID if running, empty if free
    Fallback: netstat -an | grep 3000 (macOS compatibility)

Port 8000 (Backend):
    Command: lsof -i :8000 2>/dev/null | grep -E "python|uvicorn"
    Result: PID if running, empty if free
    Fallback: netstat -an | grep 8000
```

### 5.2 Port Cleanup Sequence

```
For each port (3000 and 8000):

Step 1: Identify Process
    lsof -i :[port] → extract PID
    If empty → port free, continue

Step 2: Graceful Termination (SIGTERM)
    kill -15 [PID]
    Wait 3-5 seconds
    Check if process still exists

Step 3: Forced Termination (SIGKILL)
    If still exists → kill -9 [PID]
    Wait 1 second
    Verify removal

Step 4: Verify Port Free
    lsof -i :[port] → must be empty
    If not empty → port occupied by unknown process
    → Warn user, offer manual intervention

Step 5: Final Verification
    Retry count: 3 attempts
    Delay between retries: 2 seconds
    Timeout total: ~10 seconds per port
```

### 5.3 Port Binding Verification (Post-Startup)

```
After service startup initiated:

For Backend (Port 8000):
    Wait 2 seconds
    Check: lsof -i :8000 | grep uvicorn
    Expected: Single line with uvicorn process
    Timeout: 10 seconds

For Frontend (Port 3000):
    Wait 3 seconds
    Check: lsof -i :3000 | grep node
    Expected: Single line with node process
    Timeout: 15 seconds (includes Next.js startup)

If binding fails → trigger health check timeout path
```

---

## 6. Exit Codes & Status Reporting

### 6.1 Exit Code Specification

```
Exit Code 0: SUCCESS
    - Both services started successfully
    - Both health checks passed
    - All verifications passed
    - User ready to develop/test

Exit Code 1: SHUTDOWN FAILED
    - Could not cleanly shutdown existing processes
    - Port cleanup timeout exceeded
    - Manual intervention likely required
    - No services started

Exit Code 2: BACKEND FAILED
    - Backend startup failed or health check failed
    - Frontend may be running (check status)
    - Backend logs available at logs/backend.log
    - Next.js frontend operational for non-API tasks

Exit Code 3: FRONTEND FAILED
    - Frontend startup failed or health check failed
    - Backend may be running (check status)
    - Frontend logs available at logs/frontend.log
    - API functional but UI inaccessible

Exit Code 4: FATAL ERROR
    - Multiple critical failures
    - Unrecoverable system state
    - Script cannot proceed
    - Check logs/restart.log for root cause
```

### 6.2 Status Report Output

**On Success (Exit 0):**
```
============================================
    RESTART SUCCESSFUL
============================================

✓ Backend API (FastAPI)
  └─ http://localhost:8000
  └─ Health: http://localhost:8000/health
  └─ Docs: http://localhost:8000/docs

✓ Frontend (Next.js)
  └─ http://localhost:3000

Startup Time: 12.5 seconds
Log Files:
  └─ Backend: logs/backend.log
  └─ Frontend: logs/frontend.log

Ready to develop! Press Ctrl+C to stop services.
============================================
```

**On Partial Failure (Exit 2 or 3):**
```
============================================
    RESTART PARTIALLY SUCCESSFUL
============================================

✓ Frontend (Next.js)
  └─ http://localhost:3000

✗ Backend API (FastAPI)
  └─ FAILED TO START
  └─ Check logs/backend.log for details
  └─ Common issues:
     - Virtual environment not activated
     - Port 8000 still occupied
     - Python dependencies missing

Manual restart:
  cd backend
  source venv/bin/activate
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

============================================
```

**On Complete Failure (Exit 4):**
```
============================================
    RESTART FAILED
============================================

Both services failed to start.
Check logs/restart.log for execution details.

Issue: [Specific error from logs]

Manual troubleshooting steps:
1. Review logs/restart.log for startup sequence
2. Check port availability: lsof -i :3000 and lsof -i :8000
3. Verify directory structure and virtual environment
4. Try manual startup in separate terminals

Next steps: [Contextual advice based on error]
============================================
```

### 6.3 Service Status Verification Display

```
During Execution (live feedback):
    [14:35:22] Pre-flight validation...
    [14:35:22] ✓ Directories accessible
    [14:35:22] ✓ Ports available
    [14:35:22] Cleaning up existing processes...
    [14:35:23] ✓ Port 3000 freed (was: PID 1234)
    [14:35:25] ✓ Port 8000 freed (was: PID 5678)
    [14:35:25] Starting services...
    [14:35:25] → Backend startup (pid: 9012)
    [14:35:26] → Frontend startup (pid: 9034)
    [14:35:28] Waiting for services to initialize...
    [14:35:31] Checking backend health...
    [14:35:32] ✓ Backend responding
    [14:35:35] ✓ Frontend responding
    [14:35:35] ✓ All services healthy!
```

---

## 7. Implementation Patterns

### 7.1 Function Modularization Pattern

```
Main Script Structure:
    ├── main()
    │   ├── setup_logging()
    │   ├── validate_environment()
    │   ├── cleanup_existing_services()
    │   ├── start_backend()
    │   ├── start_frontend()
    │   ├── wait_for_services()
    │   ├── check_health()
    │   └── report_status()
    │
    ├── cleanup_existing_services()
    │   ├── find_process_on_port()
    │   ├── terminate_process()
    │   └── verify_port_free()
    │
    ├── start_backend()
    │   ├── verify_venv_exists()
    │   ├── start_service()
    │   └── capture_pid()
    │
    ├── start_frontend()
    │   ├── verify_node_modules()
    │   ├── start_service()
    │   └── capture_pid()
    │
    ├── check_health()
    │   ├── check_backend_health() [parallel]
    │   ├── check_frontend_health() [parallel]
    │   └── aggregate_results()
    │
    ├── find_process_on_port(port)
    │   ├── Try: lsof -i :[port]
    │   └── Fallback: netstat methods
    │
    ├── terminate_process(pid, timeout)
    │   ├── Send SIGTERM
    │   ├── Wait with exponential backoff
    │   ├── Send SIGKILL if needed
    │   └── Verify removal
    │
    ├── http_health_check(url, max_attempts, timeout)
    │   ├── Attempt HTTP request
    │   ├── Parse response code
    │   ├── Retry with backoff
    │   └── Return success/failure
    │
    └── log_message(section, level, message)
        ├── Format with timestamp
        ├── Write to file
        └── Write to stdout
```

### 7.2 Parallel Execution Pattern

```
Health Check Parallelization:

    Main Script
        ↓
    Launch Backend Check
    (background process, timeout 60s)
        ↓
    Launch Frontend Check
    (background process, timeout 60s)
        ↓
    Wait for Both (whichever completes first or both timeout)
        ├─ Use: wait command with process monitoring
        ├─ Or: Named pipes for IPC
        ├─ Or: Separate background jobs with check loop
        └─ Ensure both complete before proceeding

    Implementation approach:
        backend_check() &
        backend_pid=$!

        frontend_check() &
        frontend_pid=$!

        wait $backend_pid
        backend_result=$?

        wait $frontend_pid
        frontend_result=$?

        # Aggregate results
        final_status=$((backend_result + frontend_result))
```

---

## 8. System Dependencies & Prerequisites

### 8.1 Required Commands

```
Core Utilities:
    - bash (script interpreter)
    - curl (HTTP requests for health checks)
    - lsof (list open files, port detection)
    - kill (process termination)
    - grep, sed (text processing)
    - mkdir, cd, pwd (file system)
    - date (timestamp generation)

Python Stack:
    - python3.9+ (venv activation)
    - venv module (virtual environment)
    - uvicorn (ASGI server, in venv)

Node Stack:
    - node (JavaScript runtime)
    - npm (package manager)
    - next (Next.js CLI, via npm)

macOS Specific:
    - lsof availability (comes with macOS)
    - Fallback to netstat if lsof unavailable
```

### 8.2 Directory Structure Validation

```
Required Structure:
    ├── backend/
    │   ├── venv/
    │   │   ├── bin/
    │   │   │   └── activate
    │   │   └── lib/
    │   ├── app/
    │   │   └── main.py
    │   └── requirements.txt
    │
    ├── frontend/
    │   ├── node_modules/ (or check package.json)
    │   ├── package.json
    │   └── next.config.js (optional)
    │
    └── logs/ (created if missing)
```

### 8.3 Environment Validation

```
Checks before startup:

1. Script Location
   └─ Verify script is in project root
   └─ Set PROJECT_ROOT dynamically

2. Directory Accessibility
   └─ backend/ directory exists and readable
   └─ frontend/ directory exists and readable
   └─ logs/ directory can be created

3. Port Availability
   └─ Port 3000 either free or has Node process
   └─ Port 8000 either free or has Python process

4. Virtual Environment
   └─ backend/venv/ directory exists
   └─ backend/venv/bin/activate executable

5. Node Modules (optional but recommended)
   └─ frontend/node_modules exists
   └─ Warn if missing (may cause long initial startup)

6. Dependencies
   └─ Python: 3.9+
   └─ Node: 14.0.0+
   └─ Bash: 4.0+
```

---

## 9. Configuration & Customization Points

### 9.1 Configurable Parameters

```
Timing Parameters:
    BACKEND_STARTUP_DELAY=3          # seconds to wait before health check
    FRONTEND_STARTUP_DELAY=5         # seconds to wait before health check
    HEALTH_CHECK_TIMEOUT=60          # seconds before giving up
    HEALTH_CHECK_INTERVAL=2          # seconds between retry attempts
    PROCESS_SHUTDOWN_TIMEOUT=5       # seconds for graceful shutdown
    PORT_CHECK_RETRY=3               # attempts to verify port free

Service Configuration:
    BACKEND_PORT=8000                # uvicorn port
    FRONTEND_PORT=3000               # Next.js port
    BACKEND_HOST=0.0.0.0             # uvicorn host
    BACKEND_DIR=backend              # relative path to backend
    FRONTEND_DIR=frontend            # relative path to frontend
    VENV_PATH=backend/venv           # relative path to venv

Logging Configuration:
    LOG_DIR=logs                      # log directory
    BACKEND_LOG=logs/backend.log      # backend output file
    FRONTEND_LOG=logs/frontend.log    # frontend output file
    RESTART_LOG=logs/restart.log      # script execution log
    VERBOSE=false                     # enable debug output

Health Check Configuration:
    BACKEND_HEALTH_URL=http://localhost:8000/health
    FRONTEND_HEALTH_URL=http://localhost:3000
    HEALTH_CHECK_METHOD=GET           # HTTP method
    CURL_TIMEOUT=3                    # curl timeout per attempt
```

### 9.2 Optional Flags/Arguments

```
Usage: ./restart.sh [OPTIONS]

Options:
    --help, -h              Show usage information
    --verbose, -v           Enable debug output
    --clean                 Remove logs before restart
    --no-frontend           Start only backend
    --no-backend            Start only frontend
    --health-only           Run health checks without restart
    --timeout [seconds]     Override health check timeout
    --logs                  Show logs after startup
    --monitor               Keep terminal open showing logs
```

---

## 10. Failure Scenarios & Recovery Paths

### 10.1 Common Failure Scenarios

**Scenario 1: Port Already in Use (Unknown Process)**
```
Detection: netstat shows port in use, PID not matching app
Impact: Service startup fails
Recovery Path:
    1. Script detects unknown process
    2. Offers: (a) Manual kill, (b) Use different port, (c) Abort
    3. If manual kill selected: ask for confirmation
    4. Retry startup with timeout
    5. Report results
```

**Scenario 2: Virtual Environment Corrupted**
```
Detection: venv/bin/activate fails or venv/lib missing
Impact: Backend fails to start
Recovery Path:
    1. Detect: activation command returns error
    2. Log specific error
    3. Offer manual recovery:
       - Recreate: python3 -m venv backend/venv
       - Reinstall: pip install -r requirements.txt
    4. Suggest manual startup
    5. Report status
```

**Scenario 3: Dependencies Missing**
```
Detection: uvicorn or npm command not found after activation
Impact: Service fails to start
Recovery Path:
    1. Detect: command not found error in log
    2. Identify: which dependency missing
    3. Offer: pip install -r requirements.txt (backend)
    4. Offer: npm install (frontend)
    5. Retry startup
    6. Report results
```

**Scenario 4: Health Check Timeout**
```
Detection: Service port responds but health endpoint fails
Impact: Service started but unhealthy
Recovery Path:
    1. Extend retry window: +30 seconds additional attempts
    2. Check: Process still alive? Port still bound?
    3. If process died: report crash, show logs
    4. If slow: report slow startup, allow user to wait
    5. Offer: manual health check command or skip
```

**Scenario 5: Disk Space Exhausted**
```
Detection: Write to log fails
Impact: Logging unavailable, script may hang
Recovery Path:
    1. Detect: write error on first log attempt
    2. Switch: output to STDOUT only (skip file logging)
    3. Warn: disk space critical
    4. Continue: startup attempt (services may work)
    5. Report: status and warning
```

### 10.2 Recovery Decision Tree

```
Service Startup Fails
    ↓
Is port available?
    ├─ NO: Offer manual cleanup, retry
    └─ YES: Continue

Does venv exist?
    ├─ NO: Offer recreation
    └─ YES: Continue

Service starts (port bound)?
    ├─ YES: Health check timeout, offer extended wait
    └─ NO: Report failure, show logs

Health check fails?
    ├─ YES: Extend timeout, retry
    └─ NO: Report success

Max retries exceeded?
    ├─ YES: Report failure
    └─ NO: Retry with longer interval
```

---

## 11. Performance & Timing Specifications

### 11.1 Target Execution Times

```
Successful Execution Target: 15-20 seconds

Breakdown:
    Pre-flight validation:          1-2 seconds
    Process cleanup:                2-5 seconds
    Backend startup:                2-3 seconds
    Frontend startup:               3-5 seconds
    Health check (both parallel):   3-5 seconds
    Status reporting:               1 second
    ─────────────────────────────
    Total target:                   15-20 seconds

Actual times vary based on:
    - Existing process cleanup complexity
    - Next.js build cache (cold vs warm)
    - System resource availability
    - Network latency (health checks)
```

### 11.2 Timeout Specification

```
Cleanup Phase:
    SIGTERM wait: 3-5 seconds
    SIGKILL wait: 1 second
    Port verification: 10 seconds total (3 retries × 2s delay)

Startup Phase:
    Backend initialization: 5 seconds (before health check)
    Frontend build: 8 seconds (before health check)

Health Check Phase:
    Initial delay: 3-5 seconds (service warmup)
    Per attempt: 3-5 seconds (HTTP timeout)
    Total window: 60 seconds (12 retry attempts)
    Between attempts: Exponential backoff (2, 3, 4, 5+ seconds)
```

---

## 12. Monitoring & Observability

### 12.1 What to Monitor During Execution

```
Real-time Metrics:
    - Process creation: Log PID immediately
    - Port binding: Verify within 10 seconds
    - Health endpoint response: Log response time
    - Error messages: Capture first error
    - Startup duration: Total elapsed time

Logs to Maintain:
    - All stdout/stderr from both services
    - Health check attempts and responses
    - Process termination results
    - Exit codes and status
```

### 12.2 User Feedback During Execution

```
Progress Indicators (printed to STDOUT):
    [progress] Phase entering
    [progress] ✓ Checkpoint completed
    [progress] ✗ Error encountered
    [progress] ⏳ Waiting for service
    [progress] → Action being taken

Timing Info:
    Start time
    Current phase duration
    Total elapsed time
    Estimated time remaining

Error Info (if applicable):
    Error type
    Affected service
    Log file location
    Recovery options
```

---

## 13. Post-Startup State

### 13.1 Successful Startup State

```
Expected System State:
    ├─ Backend (Port 8000):
    │   ├─ Process: Running (PID logged)
    │   ├─ Virtual Env: Activated
    │   ├─ Listening: 0.0.0.0:8000
    │   ├─ Reloading: Enabled (if --reload passed)
    │   └─ Status: Responding to requests
    │
    ├─ Frontend (Port 3000):
    │   ├─ Process: Running (PID logged)
    │   ├─ Node Env: development (npm run dev)
    │   ├─ Listening: localhost:3000
    │   ├─ HMR: Hot module reloading enabled
    │   └─ Status: Serving pages
    │
    ├─ Logs:
    │   ├─ backend.log: Live uvicorn output
    │   ├─ frontend.log: Live npm output
    │   └─ restart.log: Full execution transcript
    │
    └─ Network State:
        ├─ Both services isolated (not containerized)
        ├─ Frontend → Backend: CORS configured
        └─ User machine: Full network access
```

### 13.2 User Next Steps

```
Development Workflow:
    1. Services running in background
    2. User modifies code
    3. Backend: Uvicorn auto-reload detects changes
    4. Frontend: Next.js HMR detects changes
    5. Browser: Auto-refresh shows updates
    6. Testing: User accesses localhost:3000 and localhost:8000

Stopping Services:
    Option 1: Ctrl+C in same terminal (requires foreground)
    Option 2: Kill PIDs manually: kill [backend_pid] [frontend_pid]
    Option 3: Stop ports: lsof -i :3000 | kill, lsof -i :8000 | kill
    Option 4: Wait for next restart (old processes replaced)

Troubleshooting:
    If issues appear:
        1. Check logs/backend.log and logs/frontend.log
        2. Verify ports: lsof -i :3000 and lsof -i :8000
        3. Check processes: ps aux | grep python or npm
        4. Manual restart: Run script again
```

---

## 14. Design Rationale & Trade-offs

### 14.1 Key Design Decisions

**Decision 1: Sequential Startup, Parallel Health Checks**
```
Rationale:
    - Sequential startup: Ensures predictable order, simplifies troubleshooting
    - Parallel health checks: Minimizes total execution time (critical path optimization)
    - Benefit: Combines reliability with speed

Alternative Considered:
    - Fully parallel startup: Faster but harder to debug
    - Sequential health checks: Slower (adds 2-3 seconds)
```

**Decision 2: Port-based Process Identification**
```
Rationale:
    - Reliable method on macOS
    - Works regardless of exact command-line args
    - Clean detection of "any process on port X"

Alternative Considered:
    - Process name matching: Fragile (variations in command)
    - PID file tracking: Requires pre-existing infrastructure
```

**Decision 3: Graceful Shutdown First, Force Kill Second**
```
Rationale:
    - SIGTERM gives processes chance to cleanup (resource safety)
    - SIGKILL as fallback ensures process removal (robustness)
    - Balances safety and reliability

Alternative Considered:
    - Immediate SIGKILL: Faster but risky (resource leaks)
    - User confirmation: Slower, less automation-friendly
```

**Decision 4: Health Check via HTTP Endpoints**
```
Rationale:
    - Verifies service is actually responsive (not just running)
    - Backend has /health endpoint (as specified)
    - Frontend response indicates Next.js is serving
    - More reliable than port-open check

Alternative Considered:
    - Port binding check only: Less reliable (port open ≠ ready)
    - Process alive check: Can't detect startup errors
```

**Decision 5: Exponential Backoff with Plateau**
```
Rationale:
    - Early retries (2, 3, 4 seconds): Catches quick failures
    - Plateau at 5 seconds: Prevents hammering slow services
    - Total 60-second window: Balances patience with timeout

Alternative Considered:
    - Linear backoff: Less efficient
    - Fixed interval: Either too aggressive or too slow
```

### 14.2 Known Limitations & Acceptable Trade-offs

```
Limitation 1: No Service Process Management
    - Services not daemonized (no systemd unit)
    - User must manually stop with Ctrl+C or kill PIDs
    - Trade-off: Simplicity vs. background management
    - Rationale: Development environment (not production)

Limitation 2: No Service Auto-Recovery
    - If service crashes, script doesn't restart it
    - Trade-off: Simplicity vs. resilience
    - Rationale: User should see crashes (debugging needed)

Limitation 3: No Cross-Platform Support (macOS only)
    - Uses lsof (macOS standard, not universal)
    - Doesn't support Windows or Linux by default
    - Trade-off: Simplicity vs. portability
    - Rationale: Project specified macOS development

Limitation 4: Log Files Not Rotated
    - Overwrites logs on each restart
    - Trade-off: Storage vs. history
    - Rationale: Development environment (short sessions)

Limitation 5: No Service Authentication
    - Health checks are unauthenticated
    - Trade-off: Simplicity vs. security
    - Rationale: Development environment (localhost only)
```

---

## 15. Summary & Implementation Checklist

### 15.1 Architecture Summary

The restart script is designed as a **linear orchestrator** that:

1. **Validates** the environment (pre-flight checks)
2. **Cleans** existing processes (graceful → force shutdown)
3. **Launches** both services sequentially with PID capture
4. **Waits** for initialization windows
5. **Checks** both services in parallel via HTTP health endpoints
6. **Reports** comprehensive status to user
7. **Exits** with appropriate code and provides next steps

### 15.2 Key Architectural Principles

- **Simplicity**: Single-threaded orchestration, no complex state machines
- **Reliability**: Multiple detection methods, graceful degradation
- **Observability**: Detailed logging of every phase and decision
- **Extensibility**: Configurable parameters for future customization
- **User-Friendly**: Clear progress indicators and error messages
- **Development-Focused**: Quick iteration, visible logs, easy troubleshooting

### 15.3 Implementation Checklist

```
Core Functionality:
    ☐ Pre-flight validation logic
    ☐ Process detection (lsof based)
    ☐ SIGTERM/SIGKILL logic with retry
    ☐ Port verification
    ☐ Backend service startup
    ☐ Frontend service startup
    ☐ Concurrent health checks
    ☐ HTTP request logic with retry
    ☐ Status reporting with exit codes

Logging:
    ☐ Logs/ directory creation
    ☐ Timestamp generation utility
    ☐ Script logging (restart.log)
    ☐ Backend output capture
    ☐ Frontend output capture
    ☐ Log file rotation/cleanup

Error Handling:
    ☐ Shutdown error cases
    ☐ Startup error cases
    ☐ Health check timeout logic
    ☐ Graceful degradation on failures
    ☐ Error-specific recovery paths
    ☐ User guidance for manual intervention

Testing:
    ☐ Happy path (both services start cleanly)
    ☐ Port already in use (before cleanup)
    ☐ Venv missing or broken
    ☐ Dependencies missing
    ☐ Health check timeout
    ☐ Service crashes during health check
    ☐ One service fails, other succeeds
    ☐ Log file operations
```

This architecture specification provides a complete blueprint for implementation while maintaining flexibility for development and refinement.
