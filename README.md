# Publer MCP 🚀

A comprehensive Model Context Protocol (MCP) server for the Publer social media management platform. This integration provides AI agents with powerful, intent-based tools for automated social media publishing, content optimization, and campaign management.

## ✨ Features

### 🔧 **Account Management Tools**
- **Account Status Verification** - Check API connectivity and workspace access
- **Platform Discovery** - List connected social media accounts with capabilities

### 📅 **Intelligent Scheduling Tools**  
- **Blog-to-Social Promotion** - Automatically extract blog metadata and create optimized social posts
- **Multi-Platform Publishing** - Schedule content across multiple platforms with platform-specific optimizations
- **Bulk Content Series** - Schedule content series with intelligent timing distribution
- **Optimal Time Scheduling** - AI-powered posting time optimization based on analytics

### 📊 **Job Monitoring & Analytics**
- **Real-time Job Status** - Track async publishing jobs with detailed progress updates  
- **Recent Jobs Overview** - Monitor workspace activity with success rate analytics
- **Engagement Tracking** - View post performance and engagement metrics

---

## 🛠️ Installation

### Prerequisites
- Python 3.12+
- Publer account with API access (Enterprise/Ambassador tier required)
- Publer API key and Workspace ID

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/Spinnable-AI/publer-mcp.git
cd publer-mcp
```

2. **Install dependencies:**
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

3. **Configure environment variables:**
```bash
# Create .env file
echo "PUBLER_API_BASE_URL=https://app.publer.com/api/v1/" > .env
```

4. **Run the server:**
```bash
# Development mode
make dev

# Production mode  
uv run publer_mcp/server.py
```

---

## 🔑 Authentication

Publer MCP uses **request-scoped authentication** for multi-user security. Each request must include:

### Required Headers:
```
x-api-key: YOUR_PUBLER_API_KEY
x-workspace-id: YOUR_WORKSPACE_ID  
```

### Alternative Authentication:
```
Authorization: Bearer YOUR_PUBLER_API_KEY
x-workspace-id: YOUR_WORKSPACE_ID
```

### Getting Your Credentials:
1. **API Key**: Go to Publer Dashboard → Settings → Access & Login → API Keys
2. **Workspace ID**: Found in your Publer workspace URL or available via `publer_check_account_status`

---

## 🎯 Tools Reference

### Account Management

#### `publer_check_account_status`
Verify your integration and get account overview.

**Purpose:** Integration health check and workspace discovery

**Authentication Required:** API key only

**Example Response:**
```json
{
  "status": "connected",
  "account": {
    "user_id": "12345",
    "email": "user@example.com", 
    "account_type": "enterprise"
  },
  "workspaces": {
    "available_workspaces": 3,
    "workspace_list": [
      {"id": "ws1", "name": "Marketing Team", "role": "admin"}
    ]
  }
}
```

#### `publer_list_connected_platforms`
Discover available social media accounts for posting.

**Purpose:** Platform capability discovery and validation

**Authentication Required:** API key + workspace ID

**Example Response:**
```json
{
  "status": "success",
  "platforms": [
    {
      "account_id": "acc123",
      "platform": "twitter",
      "account_name": "@company", 
      "status": "active",
      "posting_capabilities": ["text", "image", "video"]
    }
  ],
  "summary": {
    "total_platforms": 5,
    "active_platforms": 4,
    "supported_content_types": ["text", "image", "video", "link"]
  }
}
```

---

### Intelligent Scheduling

#### `publer_blog_to_twitter_scheduler`
Promote blog posts with automatic metadata extraction and platform optimization.

**Purpose:** Blog promotion and content marketing automation  

**Parameters:**
- `blog_url` (required): Blog post URL to promote
- `twitter_message` (required): Custom promotional message (≤280 chars)  
- `target_platforms`: Platform account IDs (defaults to Twitter accounts)
- `schedule_time`: ISO datetime for scheduling (optional, immediate if not provided)
- `include_blog_preview`: Include blog preview image (default: true)

**Example Usage:**
```python
await publer_blog_to_twitter_scheduler(
    blog_url="https://company.com/blog/new-product-launch",
    twitter_message="Excited to announce our new product! Check out the details:",
    target_platforms=["twitter_acc_123", "linkedin_acc_456"],
    schedule_time="2024-01-15T10:00:00Z",
    include_blog_preview=True
)
```

**Example Response:**
```json
{
  "status": "job_submitted",
  "job_id": "job_abc123",
  "scheduled_posts": [
    {
      "platform": "twitter",
      "account_id": "twitter_acc_123",
      "content": "Excited to announce our new product! Check out the details: https://company.com/blog/new-product-launch",
      "media": ["https://company.com/blog/preview.jpg"],
      "scheduled_time": "2024-01-15T10:00:00Z"
    }
  ],
  "blog_analysis": {
    "title": "Introducing Our Revolutionary New Product",
    "preview_image": "https://company.com/blog/preview.jpg", 
    "keywords": ["product", "launch", "innovation"]
  }
}
```

#### `publer_multi_platform_scheduler`
Schedule content across multiple platforms with automatic optimization.

**Purpose:** Cross-platform content distribution with platform-specific adaptations

**Parameters:**
- `content` (required): Main content text for all platforms
- `target_platforms` (required): List of platform account IDs
- `platform_customizations`: Platform-specific content overrides
- `media_urls`: Media files to attach
- `schedule_time`: ISO datetime for scheduling

**Example Usage:**
```python
await publer_multi_platform_scheduler(
    content="🎉 We're thrilled to share some exciting news with our community!",
    target_platforms=["twitter_123", "linkedin_456", "instagram_789"],
    platform_customizations={
        "linkedin": {"content": "We're excited to share a professional milestone with our network."},
        "instagram": {"content": "🎉 Exciting news! Can't wait to share more details soon! ✨"}
    },
    media_urls=["https://example.com/announcement.jpg"],
    schedule_time="2024-01-15T14:00:00Z"
)
```

#### `publer_bulk_content_series_scheduler`  
Schedule content series with intelligent timing distribution.

**Purpose:** Content campaigns, series publishing, and automated scheduling

**Parameters:**
- `content_series` (required): Array of content objects with 'content' field
- `target_platforms` (required): Platform account IDs for all posts  
- `schedule_pattern`: "daily", "weekly", "custom", or "immediate"
- `start_date`: ISO start date (required for scheduled patterns)
- `time_spacing`: Hours between posts (1-168 hours)
- `randomize_timing`: Add ±30min variance to post times

**Example Usage:**
```python
await publer_bulk_content_series_scheduler(
    content_series=[
        {"content": "Day 1: Introduction to our 5-day challenge! 💪"},
        {"content": "Day 2: Setting your goals - make them SMART! 🎯"},
        {"content": "Day 3: Building momentum with small wins 🏆"},
        {"content": "Day 4: Overcoming obstacles and staying focused 🧗"},
        {"content": "Day 5: Celebrating your progress! 🎉"}
    ],
    target_platforms=["twitter_123", "linkedin_456"],
    schedule_pattern="daily",
    start_date="2024-01-15T09:00:00Z",
    time_spacing=24,
    randomize_timing=True
)
```

#### `publer_optimal_time_scheduler`
Schedule content at optimal times using AI-powered analytics.

**Purpose:** Maximize engagement through data-driven scheduling

**Parameters:**
- `content` (required): Content to schedule  
- `target_platforms` (required): Platform account IDs to analyze
- `optimization_goal`: "engagement", "reach", "clicks", or "general"
- `timezone`: Target timezone (e.g., "America/New_York", "Europe/London")
- `date_range`: "next_24h", "next_48h", "next_7_days", "next_14_days"
- `fallback_time`: Backup time if optimization fails

**Example Usage:**
```python
await publer_optimal_time_scheduler(
    content="🚀 Just launched our new feature! Here's what makes it special:",
    target_platforms=["twitter_123", "linkedin_456"],
    optimization_goal="engagement", 
    timezone="America/New_York",
    date_range="next_7_days"
)
```

**Example Response:**
```json
{
  "status": "optimized_job_submitted",
  "job_id": "opt_789",
  "optimization_results": {
    "selected_time": "2024-01-16T15:30:00-05:00",
    "average_confidence": 0.87,
    "recommended_times": [
      {
        "platform": "twitter",
        "optimal_time": "2024-01-16T15:30:00-05:00",
        "confidence": 0.89,
        "expected_engagement": "high",
        "reasoning": "Peak audience activity based on historical data"
      }
    ]
  }
}
```

---

### Job Monitoring

#### `publer_check_job_status`
Monitor individual job progress and results.

**Purpose:** Track async job status, results, and engagement metrics

**Parameters:**  
- `job_id` (required): Job ID returned from scheduling tools

**Example Usage:**
```python
await publer_check_job_status(job_id="job_abc123")
```

**Example Response:**
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "status_message": "Job completed successfully. All 3 posts published.",
  "progress": {
    "total_posts": 3,
    "completed_posts": 3, 
    "failed_posts": 0,
    "progress_percentage": 100
  },
  "results": [
    {
      "platform": "twitter",
      "post_id": "tw_12345",
      "status": "published",
      "published_at": "2024-01-15T10:00:00Z",
      "engagement": {
        "likes": 25,
        "shares": 5,
        "comments": 3
      },
      "post_url": "https://twitter.com/user/status/12345"
    }
  ]
}
```

#### `publer_monitor_recent_jobs`
Overview of recent workspace activity and job analytics.

**Purpose:** Workspace monitoring, success rate tracking, troubleshooting

**Parameters:**
- `limit`: Number of jobs to return (1-50, default: 10)
- `status_filter`: "all", "pending", "completed", "failed", "in_progress"  
- `time_range`: "1h", "6h", "24h", "7d", "30d"

**Example Usage:**
```python
await publer_monitor_recent_jobs(
    limit=20,
    status_filter="all", 
    time_range="24h"
)
```

**Example Response:**
```json
{
  "status": "success",
  "recent_jobs": [
    {
      "job_id": "job_123",
      "job_type": "multi_platform_scheduler",
      "status": "completed",
      "created_at": "2024-01-15T09:00:00Z",
      "platforms": ["twitter", "linkedin"],
      "posts_count": 2
    }
  ],
  "summary": {
    "total_jobs": 20,
    "completed": 18,
    "failed": 1,
    "pending": 1,
    "success_rate": "90%"
  },
  "attention_needed": [
    {
      "job_id": "job_failed", 
      "reason": "Job failed",
      "action": "Check job details and retry if needed"
    }
  ]
}
```

---

## 🏗️ Architecture

### Multi-User Security
- **Request-scoped credentials** - No static credential storage
- **Workspace isolation** - Each request operates within specified workspace
- **Header-based authentication** - Secure credential passing via headers

### Async Job Management  
- **Immediate job submission** - All publishing tools return `job_id` immediately
- **Comprehensive tracking** - Monitor progress, results, and engagement metrics
- **Timeout handling** - Proper error handling for long-running operations
- **Batch operations** - Support for bulk content scheduling

### Platform Optimization
- **Content adaptation** - Automatic platform-specific content optimization
- **Media filtering** - Platform capability-aware media handling  
- **Engagement optimization** - Historical data analysis for optimal timing
- **Rate limiting** - Built-in respect for Publer API rate limits (100 req/2min)

### Error Handling
- **Comprehensive validation** - Input validation with actionable error messages
- **Graceful degradation** - Fallback mechanisms for optimization failures
- **Clear error responses** - Detailed error information with suggested actions
- **Retry guidance** - Intelligent retry recommendations for transient failures

---

## 📈 Use Cases

### Content Marketing
- **Blog Promotion**: Automatically extract blog metadata and create optimized social posts
- **Product Launches**: Schedule announcement series across multiple platforms  
- **Event Marketing**: Optimal timing for maximum event visibility
- **Thought Leadership**: Multi-platform content distribution with professional optimization

### Social Media Management
- **Campaign Automation**: Bulk schedule content series with intelligent timing
- **Multi-Platform Presence**: Consistent messaging adapted for each platform
- **Engagement Optimization**: Data-driven posting times for maximum interaction
- **Performance Monitoring**: Track job success rates and engagement metrics

### Agency & Enterprise
- **Client Campaign Management**: Workspace-isolated operations for multiple clients
- **Bulk Operations**: Handle large content volumes efficiently  
- **Analytics Integration**: Leverage historical performance data for optimization
- **Team Coordination**: Monitor team publishing activity and success rates

---

## 🔧 Development

### Development Setup
```bash
# Install development dependencies
uv sync --dev

# Run with hot reload
make dev

# Run tests
make test

# Code formatting and linting  
make lint
```

### Project Structure
```
publer_mcp/
├── tools/           # MCP tools organized by category
│   ├── account.py   # Account management tools
│   ├── scheduling.py # Blog-to-social, multi-platform scheduling  
│   ├── bulk.py      # Bulk content series scheduling
│   ├── optimization.py # Optimal time scheduling
│   └── monitoring.py   # Job status and monitoring
├── utils/           # Utility modules
│   ├── job_tracker.py    # Async job management
│   ├── content_parser.py # Blog content extraction  
│   └── time_optimizer.py # Optimal timing calculation
├── auth.py          # Centralized authentication  
├── client.py        # Thin HTTP wrapper
├── registry.py      # Tool registration
└── server.py        # FastMCP server
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Follow existing patterns and conventions  
4. Add comprehensive tests
5. Update documentation
6. Submit a pull request

---

## 📚 API Reference

### Publer API Compatibility
- **Base URL**: `https://app.publer.com/api/v1/`
- **Authentication**: `Bearer-API {api_key}` with `Publer-Workspace-Id` header  
- **Rate Limiting**: 100 requests per 2-minute fixed window
- **Async Jobs**: All publishing operations return `job_id` for tracking

### MCP Standards Compliance
- **Intent-based Design**: Tools focus on what workers want to achieve
- **Goal-oriented**: Clear business value and outcome-focused
- **Comprehensive Error Handling**: Actionable error messages and guidance
- **Multi-user Architecture**: Request-scoped security and workspace isolation
- **Production Ready**: Robust async job handling and monitoring

---

## 🆘 Troubleshooting

### Common Issues

#### Authentication Errors
```
Error: "Missing x-api-key header"
Solution: Include both x-api-key and x-workspace-id headers in requests
```

#### Rate Limiting  
```
Error: "Rate limit exceeded"
Solution: Wait 2 minutes or reduce request frequency. Publer allows 100 requests per 2-minute window.
```

#### Job Timeouts
```
Error: "Job did not complete within timeout"
Solution: Use publer_check_job_status to monitor long-running jobs. Some bulk operations may take longer.
```

#### Platform Validation
```
Error: "Invalid or disconnected platform IDs"  
Solution: Use publer_list_connected_platforms to get current active platform account IDs.
```

### Getting Help
- **Issues**: [GitHub Issues](https://github.com/Spinnable-AI/publer-mcp/issues)
- **Documentation**: [Publer API Documentation](https://app.publer.com/api/docs)
- **Community**: [Spinnable AI Discord](https://discord.gg/spinnable)

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Publer Team** - For providing comprehensive API access and documentation
- **MCP Community** - For the excellent Model Context Protocol standard  
- **Spinnable AI** - For the development framework and best practices

---

**Built with ❤️ by [Spinnable AI](https://spinnable.ai) - Making AI agents more capable, one integration at a time.**