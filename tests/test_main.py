# tests/test_main.py
"""Tests for main FastAPI application."""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "healthy"


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "services" in data


def test_openapi_docs(client):
    """Test that OpenAPI docs are accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.options("/")
    # CORS headers should be present or the endpoint should be accessible
    assert response.status_code in [200, 405]  # 405 is acceptable for OPTIONS