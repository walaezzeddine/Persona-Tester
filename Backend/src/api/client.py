"""
Frontend API Client - Calls the Backend API
This is the ONLY API code that should be in Frontend
"""

import os
from typing import Optional, Any, Dict
import httpx
import asyncio

# Backend API URL
BACKEND_URL = os.getenv("REACT_APP_API_URL", "http://localhost:5000")

class APIClient:
    """Frontend API client for Backend communication"""
    
    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request to Backend"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()
    
    async def post(self, endpoint: str, data: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """POST request to Backend"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                json=data,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE request to Backend"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{self.base_url}{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()


# Convenience functions
async def get_personas():
    """Get all personas from Backend"""
    client = APIClient()
    return await client.get("/api/personas")


async def generate_personas(url: str, num_personas: int = 3, provider: str = "ollama"):
    """Generate new personas via Backend"""
    client = APIClient()
    return await client.post(
        "/api/personas/generate",
        data={
            "url": url,
            "num_personas": num_personas,
            "provider": provider,
        }
    )


async def run_persona(persona_id: str, start_url: str):
    """Run a persona via Backend"""
    client = APIClient()
    return await client.post(
        "/api/personas/run",
        data={
            "persona_id": persona_id,
            "start_url": start_url,
        }
    )


async def get_results(result_id: str):
    """Get execution results from Backend"""
    client = APIClient()
    return await client.get(f"/api/results/{result_id}")


async def delete_persona(persona_id: str):
    """Delete a persona via Backend"""
    client = APIClient()
    return await client.delete(f"/api/personas/{persona_id}")


# Synchronous wrappers for easier use in React
def sync_get_personas():
    """Synchronous wrapper for get_personas"""
    return asyncio.run(get_personas())


def sync_generate_personas(url: str, num_personas: int = 3, provider: str = "ollama"):
    """Synchronous wrapper for generate_personas"""
    return asyncio.run(generate_personas(url, num_personas, provider))
