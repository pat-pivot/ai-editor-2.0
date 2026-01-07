"""
Image Generation and Processing Utilities for AI Editor 2.0

Uses:
- Gemini Imagen 3 (primary) for image generation
- GPT Image 1.5 (fallback) for image generation
- Cloudinary for optimization (636px width)
- Cloudflare Images for final hosting
"""

import os
import base64
import requests
import time
from typing import Optional, Tuple
from io import BytesIO

from PIL import Image


class ImageClient:
    """Image generation and processing wrapper"""

    def __init__(self):
        # OpenAI for GPT Image 1.5
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')

        # Cloudflare Images config
        self.cloudflare_account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
        self.cloudflare_api_key = os.environ.get('CLOUDFLARE_API_KEY')
        self.cloudflare_images_url = f"https://api.cloudflare.com/client/v4/accounts/{self.cloudflare_account_id}/images/v1"

        # Gemini for fallback
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')

    def generate_image(self, prompt: str) -> Tuple[Optional[bytes], str]:
        """
        Generate image from prompt using Gemini Imagen 3 (primary)
        with GPT Image 1.5 fallback.

        Args:
            prompt: Image generation prompt

        Returns:
            Tuple of (image_bytes, source) where source is 'gemini' or 'gpt'
        """
        # Try Gemini Imagen 3 first (primary)
        if self.gemini_api_key:
            try:
                image_bytes = self._generate_gemini_image(prompt)
                if image_bytes:
                    return image_bytes, 'gemini'
            except Exception as e:
                print(f"[ImageClient] Gemini Imagen 3 failed: {e}")

        # Fallback to GPT Image 1.5
        if self.openai_api_key:
            try:
                image_bytes = self._generate_gpt_image(prompt)
                if image_bytes:
                    return image_bytes, 'gpt'
            except Exception as e:
                print(f"[ImageClient] GPT Image failed: {e}")

        return None, 'none'

    def _generate_gpt_image(self, prompt: str) -> Optional[bytes]:
        """
        Generate image using GPT Image 1.5

        Fallback when Gemini Imagen 3 is unavailable
        """
        if not self.openai_api_key:
            return None

        # Enhance prompt for newsletter style
        enhanced_prompt = f"""Create a professional editorial illustration for a tech newsletter.
Style: Modern, clean, abstract representation. No text, logos, or faces.
Theme: {prompt}
Mood: Professional, informative, visually striking.
Colors: Vibrant but corporate-appropriate."""

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }

        # GPT Image 1.5 API (matches n8n workflow)
        payload = {
            "model": "gpt-image-1.5",
            "prompt": enhanced_prompt,
            "n": 1,
            "size": "1536x1024",  # 16:9 aspect ratio to match Gemini
            "response_format": "b64_json"
        }

        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            b64_image = data.get("data", [{}])[0].get("b64_json")
            if b64_image:
                return base64.b64decode(b64_image)

        print(f"[ImageClient] GPT Image API error: {response.status_code} - {response.text[:200]}")
        return None

    def _generate_gemini_image(self, prompt: str) -> Optional[bytes]:
        """
        Generate image using Gemini Imagen 3

        Primary image generator for AI Editor 2.0
        Matches n8n workflow configuration exactly.
        """
        if not self.gemini_api_key:
            return None

        # Gemini image generation endpoint (matches n8n workflow)
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.gemini_api_key
        }

        # Use prompt directly - it's already formatted by _build_image_prompt()
        # Don't add extra wrapper text like before
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "responseModalities": ["IMAGE"],  # Match n8n workflow exactly (uppercase)
                # Use aspectRatio like n8n workflow instead of imageDimensions
                "imageConfig": {
                    "aspectRatio": "16:9"
                }
            }
        }

        try:
            print(f"[ImageClient] Calling Gemini Imagen API...")
            print(f"[ImageClient]   URL: {url}")
            print(f"[ImageClient]   Prompt length: {len(prompt)} chars")

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=90  # Increased timeout for image generation
            )

            print(f"[ImageClient]   Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                # Extract base64 image from candidates response
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "inlineData" in parts[0]:
                        image_data = parts[0]["inlineData"].get("data")
                        if image_data:
                            print(f"[ImageClient]   ✓ Image data received ({len(image_data)} chars base64)")
                            return base64.b64decode(image_data)
                    else:
                        print(f"[ImageClient]   ⚠️ No inlineData in response parts")
                        print(f"[ImageClient]   Parts: {parts[:500] if parts else 'empty'}")
                else:
                    print(f"[ImageClient]   ⚠️ No candidates in response")
                    print(f"[ImageClient]   Response keys: {list(data.keys())}")
            else:
                print(f"[ImageClient]   ❌ API error: {response.status_code}")
                print(f"[ImageClient]   Response: {response.text[:500]}")

        except Exception as e:
            print(f"[ImageClient] Gemini Imagen error: {e}")
            import traceback
            print(f"[ImageClient] Traceback: {traceback.format_exc()}")

        return None

    def optimize_image(self, image_bytes: bytes, width: int = 636) -> bytes:
        """
        Optimize image using Cloudinary HTTP API with upload preset.

        Matches n8n workflow HCbd2g852rkQgSqr exactly:
        1. POST to Cloudinary with upload_preset "MakeImage"
        2. Transform URL: /upload/ → /upload/c_scale,w_636,q_auto:eco,f_webp/
        3. Fetch optimized image

        Args:
            image_bytes: Raw image bytes
            width: Target width (default 636px for newsletter)

        Returns:
            Optimized image bytes
        """
        # Cloudinary cloud name from n8n workflow
        cloud_name = "dzocuy47k"
        upload_preset = "MakeImage"
        upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"

        try:
            print(f"[ImageClient] Uploading to Cloudinary with preset '{upload_preset}' ({len(image_bytes)} bytes)...")
            print(f"[ImageClient]   URL: {upload_url}")

            # POST to Cloudinary with upload preset (matches n8n workflow exactly)
            files = {
                "file": ("image.jpg", BytesIO(image_bytes), "image/jpeg")
            }
            data = {
                "upload_preset": upload_preset
            }

            response = requests.post(upload_url, files=files, data=data, timeout=60)

            print(f"[ImageClient]   Response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                raw_url = result.get("secure_url") or result.get("url")

                if raw_url:
                    print(f"[ImageClient] ✓ Cloudinary upload success: {raw_url}")

                    # Transform URL exactly like n8n workflow:
                    # Replace /upload/ with /upload/c_scale,w_636,q_auto:eco,f_webp/
                    optimized_url = raw_url.replace(
                        "http://res.cloudinary.com",
                        "https://res.cloudinary.com"
                    ).replace(
                        "/upload/",
                        f"/upload/c_scale,w_{width},q_auto:eco,f_webp/"
                    )

                    print(f"[ImageClient]   Optimized URL: {optimized_url}")

                    # Fetch the optimized image
                    opt_response = requests.get(optimized_url, timeout=30)
                    if opt_response.status_code == 200:
                        print(f"[ImageClient] ✓ Optimized image downloaded ({len(opt_response.content)} bytes)")
                        return opt_response.content
                    else:
                        print(f"[ImageClient] ⚠️ Failed to fetch optimized: {opt_response.status_code}")
            else:
                print(f"[ImageClient] ❌ Cloudinary upload failed: {response.status_code}")
                print(f"[ImageClient]   Response: {response.text[:500]}")

        except Exception as e:
            print(f"[ImageClient] ❌ Cloudinary optimization failed: {type(e).__name__}: {e}")
            import traceback
            print(f"[ImageClient]   Traceback: {traceback.format_exc()}")

        # Fallback to local optimization
        print("[ImageClient] Using local Pillow optimization as fallback")
        return self._local_optimize(image_bytes, width)

    def _local_optimize(self, image_bytes: bytes, width: int = 636) -> bytes:
        """Local image optimization using Pillow"""
        try:
            img = Image.open(BytesIO(image_bytes))

            # Calculate new height maintaining aspect ratio
            ratio = width / img.width
            new_height = int(img.height * ratio)

            # Resize
            img = img.resize((width, new_height), Image.Resampling.LANCZOS)

            # Convert to RGB if necessary (for JPEG)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Save to bytes
            output = BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()

        except Exception as e:
            print(f"[ImageClient] Local optimization failed: {e}")
            return image_bytes

    def upload_to_cloudflare(self, image_bytes: bytes, filename: str) -> Optional[str]:
        """
        Upload image to Cloudflare Images

        Args:
            image_bytes: Image bytes to upload
            filename: Desired filename

        Returns:
            Public URL of uploaded image, or None if failed
        """
        if not self.cloudflare_account_id or not self.cloudflare_api_key:
            print("[ImageClient] Cloudflare not configured, skipping upload")
            return None

        headers = {
            "Authorization": f"Bearer {self.cloudflare_api_key}"
        }

        # Add timestamp to ID to avoid 409 conflicts on re-runs
        timestamp = int(time.time())
        unique_id = f"{filename.replace('.', '-')}-{timestamp}"

        files = {
            "file": (filename, BytesIO(image_bytes), "image/jpeg")
        }

        data = {
            "id": unique_id  # Cloudflare-friendly unique ID with timestamp
        }

        try:
            print(f"[ImageClient] Uploading to Cloudflare with ID: {unique_id}")
            response = requests.post(
                self.cloudflare_images_url,
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    # Return the public URL variant
                    variants = result.get("result", {}).get("variants", [])
                    if variants:
                        print(f"[ImageClient] ✓ Cloudflare upload success: {variants[0]}")
                        return variants[0]

            # Handle 409 conflict - resource already exists
            if response.status_code == 409:
                print(f"[ImageClient] ⚠️ Cloudflare 409 conflict - ID already exists, trying with new timestamp")
                # Try again with a different timestamp
                new_timestamp = int(time.time() * 1000)  # Use milliseconds for uniqueness
                new_unique_id = f"{filename.replace('.', '-')}-{new_timestamp}"
                data = {"id": new_unique_id}
                files = {"file": (filename, BytesIO(image_bytes), "image/jpeg")}

                retry_response = requests.post(
                    self.cloudflare_images_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=30
                )

                if retry_response.status_code == 200:
                    result = retry_response.json()
                    if result.get("success"):
                        variants = result.get("result", {}).get("variants", [])
                        if variants:
                            print(f"[ImageClient] ✓ Cloudflare retry success: {variants[0]}")
                            return variants[0]

            print(f"[ImageClient] Cloudflare upload error: {response.status_code} - {response.text[:200]}")

        except Exception as e:
            print(f"[ImageClient] Cloudflare upload failed: {e}")

        return None

    def process_image(self, prompt: str, story_id: str) -> Tuple[Optional[str], str]:
        """
        Full image processing pipeline:
        1. Generate image (Gemini Imagen 3 or GPT Image 1.5 fallback)
        2. Optimize via Cloudinary (636px width)
        3. Upload to Cloudflare

        Args:
            prompt: Image generation prompt
            story_id: Story ID for filename

        Returns:
            Tuple of (image_url, source) where source is 'gemini', 'gpt', or 'none'
        """
        # 1. Generate
        image_bytes, source = self.generate_image(prompt)
        if not image_bytes:
            return None, 'none'

        # 2. Optimize
        optimized_bytes = self.optimize_image(image_bytes)

        # 3. Upload
        filename = f"pivot5-{story_id}-{source}.jpg"
        image_url = self.upload_to_cloudflare(optimized_bytes, filename)

        if image_url:
            return image_url, source

        return None, source
