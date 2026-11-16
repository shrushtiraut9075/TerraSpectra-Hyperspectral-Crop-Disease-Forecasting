import json
import urllib.parse
import urllib.request
from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from api.schemas import FieldCreateRequest, FieldItem, LocationSearchResult
from api.services.db import list_fields
from api.services.farm_creator import create_custom_farm

router = APIRouter(prefix="/fields", tags=["fields"])


@router.get("", response_model=List[FieldItem])
def get_all_fields():
    """Returns all registered fields / farms."""
    fields = list_fields()
    return fields


@router.post("", response_model=FieldItem, status_code=status.HTTP_201_CREATED)
def create_field(payload: FieldCreateRequest):
    """Registers a new custom farm anywhere in the world and generates multi-temporal baseline."""
    if not payload.name or len(payload.name.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_NAME", "message": "Farm name is required", "details": None},
        )
    if payload.lat < -90 or payload.lat > 90 or payload.lon < -180 or payload.lon > 180:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_COORDS",
                "message": "Latitude must be [-90, 90] and Longitude [-180, 180]",
                "details": None,
            },
        )
    try:
        new_field = create_custom_farm(payload)
        return new_field
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "FARM_CREATION_FAILED",
                "message": f"Could not create farm: {str(e)}",
                "details": None,
            },
        )


@router.get("/search", response_model=List[LocationSearchResult])
def search_location(q: str = Query(..., min_length=2, description="Village, town, city, or district name")):
    """Geocodes a location query using OpenStreetMap Nominatim."""
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(q)}&limit=5"
    req = urllib.request.Request(url, headers={"User-Agent": "TerraSpectra/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            for d in data:
                results.append(
                    LocationSearchResult(
                        name=d.get("display_name", q),
                        lat=float(d.get("lat", 0.0)),
                        lon=float(d.get("lon", 0.0)),
                    )
                )
            return results
    except Exception as e:
        # Fallback if external network fails
        print(f"[Geocode Warning] {e}")
        return []

