# Migration Guide: workspace_id Parameter Architecture

## Overview

This guide documents the architectural change from **header-based** to **parameter-based** `workspace_id` in Publer MCP.

**Date:** 2025-10-03  
**Version:** 2.0.0  
**Breaking Change:** Yes  
**Backwards Compatible:** No

---

## What Changed?

### Before (Header-based)

```python
# workspace_id was extracted from x-workspace-id header
credentials = extract_publer_credentials(ctx)
# credentials.workspace_id came from header

# Tools didn't have workspace_id parameter
async def publer_list_connected_platforms(ctx: Context):
    credentials = extract_publer_credentials(ctx)
    # workspace_id automatically available from credentials
```

### After (Parameter-based)

```python
# workspace_id is NO LONGER extracted from headers
credentials = extract_publer_credentials(ctx)
# credentials only has api_key

# Tools that need workspace access must declare workspace_id parameter
async def publer_list_connected_platforms(ctx: Context, workspace_id: str):
    credentials = extract_publer_credentials(ctx)
    # workspace_id comes as explicit parameter
    headers = create_api_headers(credentials, workspace_id=workspace_id)
```

---

## Why This Change?

### Problem with Header-based Approach

1. **Inflexible:** Workers couldn't switch workspaces dynamically
2. **Implicit:** Tools didn't explicitly declare workspace dependency
3. **Hidden complexity:** Workspace requirement wasn't visible in tool signature

### Benefits of Parameter-based Approach

1. ✅ **Dynamic workspace switching:** Workers can specify different workspace per request
2. ✅ **Explicit intent:** Tool signature clearly shows workspace requirement
3. ✅ **Type safety:** workspace_id is a typed parameter, not a header string
4. ✅ **Better validation:** Parameter validation happens at tool level
5. ✅ **Clearer architecture:** Separation between authentication and workspace selection

---

## Breaking Changes

### 1. Tool Signatures

**Changed Tools:**

| Tool | Before | After |
|------|--------|-------|
| `publer_list_connected_platforms` | `ctx: Context` | `ctx: Context, workspace_id: str` |

**Unchanged Tools:**

| Tool | Signature | Reason |
|------|-----------|--------|
| `publer_check_account_status` | `ctx: Context` | User-scoped, doesn't need workspace |

### 2. Authentication Module (`publer_mcp/auth.py`)

#### PublerCredentials NamedTuple

```python
# BEFORE
class PublerCredentials(NamedTuple):
    api_key: str | None
    workspace_id: str | None  # ❌ REMOVED

# AFTER
class PublerCredentials(NamedTuple):
    api_key: str | None
    # workspace_id removed - now passed as tool parameter
```

#### extract_publer_credentials()

```python
# BEFORE - Returns credentials with workspace_id from header
credentials = extract_publer_credentials(ctx)
# credentials.workspace_id available

# AFTER - Only returns API key
credentials = extract_publer_credentials(ctx)
# credentials only has api_key
```

#### validate_workspace_access()

```python
# BEFORE - Validated both API key and workspace_id from credentials
workspace_valid, error = validate_workspace_access(credentials)

# AFTER - Function REMOVED, replaced with separate validations
api_valid, error = validate_api_key(credentials)
workspace_valid, error = validate_workspace_id(workspace_id)  # New function
```

#### create_api_headers()

```python
# BEFORE - Used include_workspace boolean flag
headers = create_api_headers(credentials, include_workspace=True)
# workspace_id came from credentials.workspace_id

# AFTER - Accepts workspace_id as explicit parameter
headers = create_api_headers(credentials, workspace_id="ws_123")
# workspace_id passed explicitly
```

---

## Migration Steps for Tool Developers

### Step 1: Identify Workspace-Scoped Tools

Determine if your tool accesses workspace-scoped endpoints:

**Workspace-Scoped Endpoints** (need workspace_id):
- `/accounts` - Social media accounts
- `/posts` - Content posts
- `/analytics` - Workspace analytics
- `/team` - Team members
- `/schedules` - Posting schedules

**User-Scoped Endpoints** (do NOT need workspace_id):
- `/users/me` - Current user info
- `/workspaces` - List of workspaces
- `/user/settings` - User preferences

### Step 2: Update Tool Signature

**For workspace-scoped tools**, add `workspace_id: str` parameter:

```python
# BEFORE
async def my_tool(ctx: Context) -> Dict[str, Any]:
    ...

# AFTER
async def my_tool(ctx: Context, workspace_id: str) -> Dict[str, Any]:
    ...
```

### Step 3: Update Imports

```python
# BEFORE
from ..auth import (
    create_api_headers,
    extract_publer_credentials,
    validate_api_key,
    validate_workspace_access,  # ❌ REMOVED
)

# AFTER
from ..auth import (
    create_api_headers,
    extract_publer_credentials,
    validate_api_key,
    validate_workspace_id,  # ✅ NEW
)
```

### Step 4: Update Validation Logic

```python
# BEFORE
credentials = extract_publer_credentials(ctx)
workspace_valid, error = validate_workspace_access(credentials)
if not workspace_valid:
    return {"status": "error", "error": error}

# AFTER
credentials = extract_publer_credentials(ctx)

# Validate API key
api_valid, api_error = validate_api_key(credentials)
if not api_valid:
    return {"status": "authentication_failed", "error": api_error}

# Validate workspace_id parameter
workspace_valid, workspace_error = validate_workspace_id(workspace_id)
if not workspace_valid:
    return {"status": "workspace_required", "error": workspace_error}
```

### Step 5: Update Header Creation

```python
# BEFORE
headers = create_api_headers(credentials, include_workspace=True)

# AFTER
headers = create_api_headers(credentials, workspace_id=workspace_id)
```

---

## Complete Tool Migration Example

### Before

```python
async def publer_list_connected_platforms(ctx: Context) -> Dict[str, Any]:
    try:
        credentials = extract_publer_credentials(ctx)
        
        # Validate both API key AND workspace ID (from header)
        workspace_valid, workspace_error = validate_workspace_access(credentials)
        if not workspace_valid:
            return {"status": "error", "error": workspace_error}
        
        client = create_client()
        
        # workspace_id came from credentials.workspace_id
        accounts_headers = create_api_headers(credentials, include_workspace=True)
        accounts = await client.get("accounts", accounts_headers)
        
        # ... rest of tool
```

### After

```python
async def publer_list_connected_platforms(
    ctx: Context, 
    workspace_id: str  # ✅ NEW PARAMETER
) -> Dict[str, Any]:
    """
    List connected platforms.
    
    Args:
        workspace_id: The Publer workspace ID to list platforms for.
    """
    try:
        credentials = extract_publer_credentials(ctx)
        
        # Validate API key
        api_valid, api_error = validate_api_key(credentials)
        if not api_valid:
            return {"status": "authentication_failed", "error": api_error}
        
        # Validate workspace_id parameter
        workspace_valid, workspace_error = validate_workspace_id(workspace_id)
        if not workspace_valid:
            return {"status": "workspace_required", "error": workspace_error}
        
        client = create_client()
        
        # workspace_id passed as parameter
        accounts_headers = create_api_headers(credentials, workspace_id=workspace_id)
        accounts = await client.get("accounts", accounts_headers)
        
        # ... rest of tool
```

---

## MCP Client Usage

### Before (Header-based)

Workers had to send workspace_id in headers:

```json
{
  "method": "tools/call",
  "params": {
    "name": "publer_list_connected_platforms",
    "arguments": {}
  },
  "headers": {
    "x-api-key": "api_key_123",
    "x-workspace-id": "workspace_456"
  }
}
```

### After (Parameter-based)

Workers send workspace_id as tool parameter:

```json
{
  "method": "tools/call",
  "params": {
    "name": "publer_list_connected_platforms",
    "arguments": {
      "workspace_id": "workspace_456"
    }
  },
  "headers": {
    "x-api-key": "api_key_123"
  }
}
```

**Benefits:**
- ✅ Workers can switch workspaces per request
- ✅ workspace_id is part of tool invocation, not authentication
- ✅ Clearer separation of concerns

---

## Testing Migration

### Run Tests

```bash
# Run all workspace_id parameter tests
pytest tests/test_workspace_id_parameter.py -v

# Run specific test class
pytest tests/test_workspace_id_parameter.py::TestCreateApiHeaders -v

# Run integration tests
pytest tests/test_workspace_id_parameter.py::TestHeaderFlowIntegration -v
```

### Manual Testing

#### Test User-Scoped Tool (No workspace_id needed)

```bash
# Should work without workspace_id parameter
curl -X POST http://localhost:8000/mcp \
  -H "x-api-key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "publer_check_account_status",
      "arguments": {}
    }
  }'
```

#### Test Workspace-Scoped Tool (workspace_id required)

```bash
# Should require workspace_id parameter
curl -X POST http://localhost:8000/mcp \
  -H "x-api-key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "publer_list_connected_platforms",
      "arguments": {
        "workspace_id": "your_workspace_id"
      }
    }
  }'
```

---

## Tool Classification Reference

### Tools That Do NOT Need workspace_id Parameter

| Tool | Endpoints | Reason |
|------|-----------|--------|
| `publer_check_account_status` | `GET /users/me`<br>`GET /workspaces` | User-scoped endpoints |

### Tools That Need workspace_id Parameter

| Tool | Endpoints | Reason |
|------|-----------|--------|
| `publer_list_connected_platforms` | `GET /accounts` | Workspace-scoped endpoint |

### Decision Tree for New Tools

```
Does the tool make API calls?
├─ NO → No workspace_id parameter needed
└─ YES → Does it access workspace-scoped endpoints?
    ├─ NO (user/account level) → No workspace_id parameter
    └─ YES (workspace resources) → ✅ Add workspace_id parameter
```

---

## Frequently Asked Questions

### Q: Why remove workspace_id from headers?

**A:** To enable dynamic workspace switching. With header-based approach, workers were locked to a single workspace per session. Parameter-based allows switching workspaces per request.

### Q: Do all tools need workspace_id parameter?

**A:** No. Only tools that access workspace-scoped endpoints (like accounts, posts, analytics) need it. User-scoped tools (like account status) don't need it.

### Q: Can I still send x-workspace-id header?

**A:** The header is ignored. You MUST pass workspace_id as a tool parameter for workspace-scoped tools.

### Q: What if I forget to add workspace_id parameter to a workspace-scoped tool?

**A:** The tool will fail when trying to access workspace endpoints, as the Publer API requires the `Publer-Workspace-Id` header for workspace-scoped operations.

### Q: How do I know if an endpoint is workspace-scoped?

**A:** Check the Publer API documentation. Generally, endpoints under `/accounts`, `/posts`, `/analytics`, `/team`, and `/schedules` are workspace-scoped.

---

## Rollback Plan

If you need to rollback to header-based architecture:

1. Checkout previous commit before migration
2. Restore `x-workspace-id` header handling
3. Update tools to remove workspace_id parameters

```bash
git checkout <commit-before-migration>
```

**Note:** Rollback is NOT recommended as the parameter-based approach is architecturally superior.

---

## Support

For questions or issues related to this migration:

1. Check the test file: `tests/test_workspace_id_parameter.py`
2. Review the implementation in `publer_mcp/auth.py`
3. Contact: sebastiao@spinnable.ai

---

## Changelog

### v2.0.0 (2025-10-03)

**Breaking Changes:**
- ❌ Removed `workspace_id` from `PublerCredentials` NamedTuple
- ❌ Removed `validate_workspace_access()` function
- ❌ Changed `create_api_headers(include_workspace=...)` to `create_api_headers(workspace_id=...)`
- ❌ Workspace-scoped tools now require explicit `workspace_id: str` parameter

**New Features:**
- ✅ Added `validate_workspace_id()` for parameter validation
- ✅ Dynamic workspace switching support
- ✅ Explicit workspace requirement in tool signatures

**Improvements:**
- ✅ Clearer separation between authentication and workspace selection
- ✅ Better type safety with explicit parameters
- ✅ Improved error handling with separate validation

---

**Migration Date:** 2025-10-03  
**Completed By:** Liam Kim  
**Approved By:** Sebastião Assunção