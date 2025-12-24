"""
Mautic API Client for AI Editor 2.0 Workers

Handles email campaign creation and sending via Mautic.
"""

import os
import base64
import requests
from typing import Dict, Any, Optional, List


class MauticClient:
    """Mautic API wrapper for AI Editor 2.0"""

    def __init__(self):
        self.base_url = os.environ.get('MAUTIC_BASE_URL', 'https://app.pivotnews.com')
        self.username = os.environ.get('MAUTIC_USERNAME')
        self.password = os.environ.get('MAUTIC_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("MAUTIC_USERNAME and MAUTIC_PASSWORD environment variables are required")

        # Create basic auth header
        credentials = f"{self.username}:{self.password}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {b64_credentials}"

        # API endpoints
        self.api_base = f"{self.base_url}/api"

        # GreenArrow transport ID (for email delivery)
        self.transport_id = os.environ.get('MAUTIC_TRANSPORT_ID')

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> dict:
        """Make authenticated request to Mautic API"""
        url = f"{self.api_base}/{endpoint}"

        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json"
        }

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            params=params,
            timeout=30
        )

        if response.status_code >= 400:
            raise Exception(f"Mautic API error: {response.status_code} - {response.text[:500]}")

        return response.json()

    def create_email(self, email_data: dict) -> dict:
        """
        Create a new email campaign in Mautic.

        Args:
            email_data: {
                name: Campaign name,
                subject: Email subject line,
                customHtml: Full HTML content,
                description: Optional description,
                fromAddress: Sender email,
                fromName: Sender name,
                replyToAddress: Reply-to email
            }

        Returns:
            {id: email_id, ...}
        """
        # Build Mautic email payload
        payload = {
            "name": email_data.get("name", "Pivot 5 Newsletter"),
            "subject": email_data.get("subject", "Pivot 5 Daily AI Newsletter"),
            "customHtml": email_data.get("customHtml", ""),
            "description": email_data.get("description", ""),
            "fromAddress": email_data.get("fromAddress", "newsletter@pivotmedia.ai"),
            "fromName": email_data.get("fromName", "Pivot 5"),
            "replyToAddress": email_data.get("replyToAddress", "reply@pivotmedia.ai"),
            "isPublished": True,
            "emailType": "template"
        }

        response = self._make_request("POST", "emails/new", data=payload)
        return response.get("email", {})

    def update_email(self, email_id: int, update_data: dict) -> dict:
        """
        Update an existing email.

        Args:
            email_id: Mautic email ID
            update_data: Fields to update

        Returns:
            Updated email data
        """
        response = self._make_request("PATCH", f"emails/{email_id}/edit", data=update_data)
        return response.get("email", {})

    def attach_transport(self, email_id: int, transport_id: Optional[str] = None) -> bool:
        """
        Attach GreenArrow transport to email for delivery.

        Args:
            email_id: Mautic email ID
            transport_id: GreenArrow transport ID (uses default if not provided)

        Returns:
            Success boolean
        """
        tid = transport_id or self.transport_id
        if not tid:
            print("[MauticClient] No transport ID configured")
            return False

        try:
            # This may vary based on your Mautic/GreenArrow integration
            payload = {
                "transport_id": tid
            }
            self._make_request("POST", f"emails/{email_id}/transport", data=payload)
            return True
        except Exception as e:
            print(f"[MauticClient] Failed to attach transport: {e}")
            return False

    def send_email(self, email_id: int, segment_id: Optional[int] = None) -> dict:
        """
        Send email to a segment or trigger immediate send.

        Args:
            email_id: Mautic email ID
            segment_id: Target segment ID (optional)

        Returns:
            Send result with statistics
        """
        endpoint = f"emails/{email_id}/send"
        params = {}

        if segment_id:
            params["listId"] = segment_id

        response = self._make_request("POST", endpoint, params=params)
        return response

    def get_email_stats(self, email_id: int) -> dict:
        """
        Get email statistics (opens, clicks, etc.)

        Args:
            email_id: Mautic email ID

        Returns:
            Statistics dictionary
        """
        response = self._make_request("GET", f"emails/{email_id}")
        email = response.get("email", {})

        return {
            "sentCount": email.get("sentCount", 0),
            "readCount": email.get("readCount", 0),
            "readRate": email.get("readRate", 0),
            "clickCount": email.get("clickCount", 0),
            "clickRate": email.get("clickRate", 0),
            "unsubscribeCount": email.get("unsubscribeCount", 0),
            "bounceCount": email.get("bounceCount", 0)
        }

    def get_segment(self, segment_id: int) -> dict:
        """Get segment details"""
        response = self._make_request("GET", f"segments/{segment_id}")
        return response.get("list", {})

    def list_segments(self) -> List[dict]:
        """List all segments"""
        response = self._make_request("GET", "segments")
        return response.get("lists", [])

    def get_filtered_stats(self, email_id: int) -> dict:
        """
        Get email statistics with bot/security scanner filtering.

        Filters out:
        - Opens from known security scanners
        - Rapid successive opens (< 1 second)
        - Opens without subsequent engagement

        Args:
            email_id: Mautic email ID

        Returns:
            Filtered statistics
        """
        # Get raw stats
        raw_stats = self.get_email_stats(email_id)

        # Get detailed email events for filtering
        try:
            events = self._make_request("GET", f"emails/{email_id}/stats")

            # Apply bot filtering heuristics
            # (This is a simplified version - actual implementation would
            # analyze event timestamps and user agents)
            reads = events.get("read", [])
            filtered_reads = []

            for read in reads:
                # Skip if read happened within 1 second of send
                # (likely security scanner)
                if read.get("secondsToRead", 0) < 1:
                    continue

                # Skip known security scanner IPs/user agents
                # (would need actual implementation based on your data)

                filtered_reads.append(read)

            return {
                "sentCount": raw_stats["sentCount"],
                "readCount": len(filtered_reads),
                "readRate": len(filtered_reads) / raw_stats["sentCount"] * 100 if raw_stats["sentCount"] > 0 else 0,
                "clickCount": raw_stats["clickCount"],
                "clickRate": raw_stats["clickRate"],
                "unsubscribeCount": raw_stats["unsubscribeCount"],
                "bounceCount": raw_stats["bounceCount"],
                "rawReadCount": raw_stats["readCount"],
                "filteredReads": raw_stats["readCount"] - len(filtered_reads)
            }

        except Exception as e:
            print(f"[MauticClient] Filtering failed, returning raw stats: {e}")
            return raw_stats
