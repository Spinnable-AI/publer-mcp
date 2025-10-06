"""
Async job tracking utilities for Publer MCP.
"""

import asyncio
import time
from typing import Any, Dict, Optional
from datetime import datetime

from ..client import PublerAPIClient, PublerAPIError, PublerJobTimeoutError


class AsyncJobTracker:
    """
    Centralized async job tracking for all publishing tools.
    
    Handles job submission, status polling, timeout management, and result processing
    for Publer's async publishing workflow.
    """
    
    @staticmethod
    async def submit_job(
        client: PublerAPIClient,
        endpoint: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Submit a job to Publer API and return standardized response.
        
        Args:
            client: Publer API client instance
            endpoint: API endpoint (e.g., 'posts/schedule')
            headers: Request headers with credentials
            payload: Job payload data
            timeout: Timeout in seconds (default: 5 minutes)
            
        Returns:
            Dict with status and job_id or error information
        """
        try:
            response = await client.post(endpoint, headers, json_data=payload)
            
            # Check if response contains job_id
            job_id = response.get("job_id")
            if job_id:
                return {
                    "status": "job_submitted",
                    "job_id": job_id,
                    "submitted_at": datetime.utcnow().isoformat(),
                    "endpoint": endpoint
                }
            
            # Handle immediate response (synchronous operation)
            if response.get("status") == "success" or "posts" in response:
                # Generate a pseudo job_id for tracking
                pseudo_job_id = f"sync_{int(time.time())}"
                return {
                    "status": "job_submitted",
                    "job_id": pseudo_job_id,
                    "submitted_at": datetime.utcnow().isoformat(),
                    "endpoint": endpoint,
                    "immediate_response": response
                }
            
            # Unexpected response format
            return {
                "status": "submission_error",
                "error": "Invalid response format from API",
                "response": response
            }
            
        except PublerAPIError as e:
            return {
                "status": "api_error",
                "error": f"API error during job submission: {str(e)}",
                "endpoint": endpoint
            }
        except Exception as e:
            return {
                "status": "submission_error", 
                "error": f"Unexpected error during job submission: {str(e)}",
                "endpoint": endpoint
            }
    
    @staticmethod
    async def poll_job_completion(
        client: PublerAPIClient,
        job_id: str,
        headers: Dict[str, str],
        timeout: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """
        Poll job status until completion with proper timeout handling.
        
        Args:
            client: Publer API client instance
            job_id: Job ID to poll
            headers: Request headers with credentials
            timeout: Maximum time to wait in seconds
            poll_interval: Seconds between status checks
            
        Returns:
            Final job result when completed or error information
        """
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    result = await client.get(f"job_status/{job_id}", headers)
                    
                    status = result.get("status")
                    if status == "completed":
                        return {
                            "status": "completed",
                            "job_id": job_id,
                            "result": result,
                            "polling_time": round(time.time() - start_time, 2)
                        }
                    elif status == "failed":
                        error_msg = result.get("error", "Job failed without specific error message")
                        return {
                            "status": "failed",
                            "job_id": job_id,
                            "error": f"Job {job_id} failed: {error_msg}",
                            "result": result,
                            "polling_time": round(time.time() - start_time, 2)
                        }
                    
                    # Job still in progress, wait before next poll
                    await asyncio.sleep(poll_interval)
                    
                except PublerAPIError as e:
                    if "404" in str(e) or "not found" in str(e).lower():
                        return {
                            "status": "job_not_found",
                            "job_id": job_id,
                            "error": f"Job {job_id} not found during polling",
                            "polling_time": round(time.time() - start_time, 2)
                        }
                    else:
                        # For other API errors, continue polling (transient issues)
                        await asyncio.sleep(poll_interval)
                
                except Exception as e:
                    # Log other errors but continue polling
                    await asyncio.sleep(poll_interval)
            
            # Timeout reached
            return {
                "status": "timeout",
                "job_id": job_id,
                "error": f"Job {job_id} did not complete within {timeout} seconds",
                "polling_time": timeout
            }
            
        except Exception as e:
            return {
                "status": "polling_error",
                "job_id": job_id,
                "error": f"Error while polling job status: {str(e)}",
                "polling_time": round(time.time() - start_time, 2)
            }
    
    @staticmethod
    async def submit_and_wait(
        client: PublerAPIClient,
        endpoint: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        timeout: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """
        Submit job and wait for completion in a single operation.
        
        Convenience method that combines submit_job and poll_job_completion.
        Use this when you need immediate results rather than async tracking.
        
        Args:
            client: Publer API client instance
            endpoint: API endpoint (e.g., 'posts/schedule')
            headers: Request headers with credentials
            payload: Job payload data
            timeout: Total timeout in seconds
            poll_interval: Seconds between status checks
            
        Returns:
            Final job result or error information
        """
        # Submit job first
        submit_result = await AsyncJobTracker.submit_job(
            client=client,
            endpoint=endpoint,
            headers=headers,
            payload=payload,
            timeout=timeout
        )
        
        if submit_result.get("status") != "job_submitted":
            return submit_result
        
        job_id = submit_result["job_id"]
        
        # If we have an immediate response, return it
        if "immediate_response" in submit_result:
            return {
                "status": "completed",
                "job_id": job_id,
                "result": submit_result["immediate_response"],
                "was_immediate": True
            }
        
        # Poll for completion
        return await AsyncJobTracker.poll_job_completion(
            client=client,
            job_id=job_id,
            headers=headers,
            timeout=timeout,
            poll_interval=poll_interval
        )
    
    @staticmethod
    def parse_job_response(job_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and standardize job response format.
        
        Args:
            job_result: Raw job result from API
            
        Returns:
            Standardized job response format
        """
        if not isinstance(job_result, dict):
            return {
                "status": "parse_error",
                "error": "Invalid job result format",
                "raw_result": job_result
            }
        
        # Extract key information
        job_status = job_result.get("status", "unknown")
        job_id = job_result.get("job_id", "unknown")
        results = job_result.get("results", [])
        errors = job_result.get("errors", [])
        
        # Calculate summary statistics
        total_posts = len(results) if results else 0
        successful_posts = len([r for r in results if r.get("status") == "published"]) if results else 0
        failed_posts = len([r for r in results if r.get("status") == "failed"]) if results else 0
        
        return {
            "job_id": job_id,
            "status": job_status,
            "summary": {
                "total_posts": total_posts,
                "successful_posts": successful_posts,
                "failed_posts": failed_posts,
                "success_rate": round((successful_posts / total_posts) * 100) if total_posts > 0 else 0
            },
            "results": results,
            "errors": errors,
            "timing": {
                "created_at": job_result.get("created_at"),
                "completed_at": job_result.get("completed_at"),
                "duration": job_result.get("duration")
            },
            "raw_result": job_result
        }


class JobBatch:
    """
    Helper class for managing multiple related jobs as a batch.
    
    Useful for bulk operations where multiple jobs are submitted simultaneously
    and need to be tracked together.
    """
    
    def __init__(self, batch_id: str, job_ids: list[str]):
        """
        Initialize job batch.
        
        Args:
            batch_id: Unique identifier for the batch
            job_ids: List of job IDs in this batch
        """
        self.batch_id = batch_id
        self.job_ids = job_ids
        self.created_at = datetime.utcnow().isoformat()
        self.completed_jobs: Dict[str, Dict[str, Any]] = {}
    
    async def poll_all_jobs(
        self,
        client: PublerAPIClient,
        headers: Dict[str, str],
        timeout: int = 300,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Poll all jobs in the batch until completion.
        
        Args:
            client: Publer API client instance
            headers: Request headers with credentials
            timeout: Timeout per job in seconds
            poll_interval: Seconds between status checks
            
        Returns:
            Batch completion summary
        """
        start_time = time.time()
        
        # Poll each job concurrently
        polling_tasks = []
        for job_id in self.job_ids:
            task = AsyncJobTracker.poll_job_completion(
                client=client,
                job_id=job_id,
                headers=headers,
                timeout=timeout,
                poll_interval=poll_interval
            )
            polling_tasks.append(task)
        
        # Wait for all jobs to complete
        results = await asyncio.gather(*polling_tasks, return_exceptions=True)
        
        # Process results
        completed_count = 0
        failed_count = 0
        
        for i, result in enumerate(results):
            job_id = self.job_ids[i]
            
            if isinstance(result, Exception):
                self.completed_jobs[job_id] = {
                    "status": "error",
                    "error": str(result)
                }
                failed_count += 1
            else:
                self.completed_jobs[job_id] = result
                if result.get("status") == "completed":
                    completed_count += 1
                else:
                    failed_count += 1
        
        total_time = round(time.time() - start_time, 2)
        
        return {
            "batch_id": self.batch_id,
            "status": "batch_completed",
            "summary": {
                "total_jobs": len(self.job_ids),
                "completed_jobs": completed_count,
                "failed_jobs": failed_count,
                "success_rate": round((completed_count / len(self.job_ids)) * 100) if self.job_ids else 0
            },
            "job_results": self.completed_jobs,
            "timing": {
                "created_at": self.created_at,
                "completed_at": datetime.utcnow().isoformat(),
                "total_time": total_time
            }
        }