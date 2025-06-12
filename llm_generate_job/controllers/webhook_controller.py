import json
import logging
import hashlib
import time
import base64
import requests
from typing import Optional

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
    from nacl.encoding import HexEncoder
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

_logger = logging.getLogger(__name__)

# FAL webhook verification constants
JWKS_URL = "https://rest.alpha.fal.ai/.well-known/jwks.json"
JWKS_CACHE_DURATION = 24 * 60 * 60  # 24 hours in seconds
_jwks_cache = None
_jwks_cache_time = 0


class WebhookController(http.Controller):
    
    @http.route('/llm/generate_job/webhook/<int:job_id>', type='json', auth='public', methods=['POST'], csrf=False)
    def generation_job_webhook(self, job_id, **kwargs):
        """Handle webhook notifications from generation providers"""
        try:
            # Get the job record
            job = request.env['llm.generate.job'].sudo().browse(job_id)
            if not job.exists():
                _logger.error(f"Job {job_id} not found for webhook")
                return {"status": "error", "message": "Job not found"}
            
            # Get webhook data
            webhook_data = request.get_json_data()
            if not webhook_data:
                _logger.error(f"No webhook data received for job {job_id}")
                return {"status": "error", "message": "No data received"}
            
            # Verify webhook if it's from FAL (has signature headers)
            if self._is_fal_webhook(request):
                if not self._verify_fal_webhook(request, webhook_data):
                    _logger.error(f"Webhook verification failed for job {job_id}")
                    return {"status": "error", "message": "Verification failed"}
            
            # Process the webhook
            job.process_webhook_result(webhook_data)
            
            _logger.info(f"Successfully processed webhook for job {job_id}")
            return {"status": "success"}
            
        except Exception as e:
            _logger.error(f"Error processing webhook for job {job_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    @http.route('/llm/generate_job/webhook/test/<int:job_id>', type='json', auth='user', methods=['POST'])
    def test_webhook(self, job_id, **kwargs):
        """Test endpoint for webhook functionality (authenticated)"""
        try:
            job = request.env['llm.generate.job'].browse(job_id)
            if not job.exists():
                return {"status": "error", "message": "Job not found"}
            
            # Simulate a successful completion
            test_data = {
                "request_id": job.external_job_id or "test-request-id",
                "gateway_request_id": job.gateway_request_id or "test-gateway-id",
                "status": "OK",
                "payload": {
                    "images": [
                        {
                            "url": "https://example.com/test-image.png",
                            "content_type": "image/png",
                            "file_name": "test-image.png",
                            "file_size": 1024,
                            "width": 512,
                            "height": 512
                        }
                    ]
                }
            }
            
            job.process_webhook_result(test_data)
            return {"status": "success", "message": "Test webhook processed"}
            
        except Exception as e:
            _logger.error(f"Error in test webhook for job {job_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def _is_fal_webhook(self, request):
        """Check if this is a FAL webhook by looking for signature headers"""
        required_headers = [
            'X-Fal-Webhook-Request-Id',
            'X-Fal-Webhook-User-Id', 
            'X-Fal-Webhook-Timestamp',
            'X-Fal-Webhook-Signature'
        ]
        return all(request.httprequest.headers.get(header) for header in required_headers)
    
    def _verify_fal_webhook(self, request, webhook_data):
        """Verify FAL webhook signature"""
        if not NACL_AVAILABLE:
            _logger.warning("PyNaCl not available, skipping webhook verification")
            return True  # Skip verification if PyNaCl is not available
        
        try:
            # Extract headers
            request_id = request.httprequest.headers.get('X-Fal-Webhook-Request-Id')
            user_id = request.httprequest.headers.get('X-Fal-Webhook-User-Id')
            timestamp = request.httprequest.headers.get('X-Fal-Webhook-Timestamp')
            signature_hex = request.httprequest.headers.get('X-Fal-Webhook-Signature')
            
            if not all([request_id, user_id, timestamp, signature_hex]):
                _logger.error("Missing required webhook headers")
                return False
            
            # Get raw body
            body = request.httprequest.get_data()
            
            return self._verify_webhook_signature(
                request_id, user_id, timestamp, signature_hex, body
            )
            
        except Exception as e:
            _logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def _verify_webhook_signature(self, request_id: str, user_id: str, timestamp: str, 
                                 signature_hex: str, body: bytes) -> bool:
        """Verify webhook signature using FAL's method"""
        try:
            # Validate timestamp (within ±5 minutes)
            timestamp_int = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - timestamp_int) > 300:
                _logger.error("Timestamp is too old or in the future")
                return False
        except ValueError:
            _logger.error("Invalid timestamp format")
            return False
        
        try:
            # Construct the message to verify
            message_parts = [
                request_id,
                user_id,
                timestamp,
                hashlib.sha256(body).hexdigest()
            ]
            
            if any(part is None for part in message_parts):
                _logger.error("Missing required header value")
                return False
                
            message_to_verify = "\n".join(message_parts).encode("utf-8")
        except Exception as e:
            _logger.error(f"Error constructing message: {e}")
            return False
        
        try:
            # Decode signature
            signature_bytes = bytes.fromhex(signature_hex)
        except ValueError:
            _logger.error("Invalid signature format (not hexadecimal)")
            return False
        
        # Fetch and verify with public keys
        try:
            public_keys_info = self._fetch_jwks()
            if not public_keys_info:
                _logger.error("No public keys found in JWKS")
                return False
        except Exception as e:
            _logger.error(f"Error fetching JWKS: {e}")
            return False
        
        # Verify signature with each public key
        for key_info in public_keys_info:
            try:
                public_key_b64url = key_info.get("x")
                if not isinstance(public_key_b64url, str):
                    continue
                    
                public_key_bytes = base64.urlsafe_b64decode(public_key_b64url)
                verify_key = VerifyKey(public_key_bytes.hex(), encoder=HexEncoder)
                verify_key.verify(message_to_verify, signature_bytes)
                return True
                
            except (BadSignatureError, Exception) as e:
                _logger.debug(f"Verification failed with a key: {e}")
                continue
        
        _logger.error("Signature verification failed with all keys")
        return False
    
    def _fetch_jwks(self) -> list:
        """Fetch and cache JWKS, refreshing after 24 hours"""
        global _jwks_cache, _jwks_cache_time
        
        current_time = time.time()
        if _jwks_cache is None or (current_time - _jwks_cache_time) > JWKS_CACHE_DURATION:
            try:
                response = requests.get(JWKS_URL, timeout=10)
                response.raise_for_status()
                _jwks_cache = response.json().get("keys", [])
                _jwks_cache_time = current_time
            except Exception as e:
                _logger.error(f"Failed to fetch JWKS: {e}")
                return _jwks_cache or []
        
        return _jwks_cache
