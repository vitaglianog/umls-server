import json
import httpx
import asyncio

BASE = "http://localhost:8000"  # or wherever your API is running

async def get_billing_codes_from_snomed(natural_language_query):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/cuis", params={"query": natural_language_query})
        r.raise_for_status()
        matches = r.json()
        result = [m for m in matches["cuis"] if m["language_code"] == "ENG"][0]

        r = await client.get(f"{BASE}/code-map/", params={"cui": result['cui']})
        r.raise_for_status()
        matches = r.json()['code_maps']
        snomed_code = [m["code"] for m in matches if m["sab"] == "SNOMEDCT_US"][0]
        billing_code = [m["code"] for m in matches if m["sab"] == "ICD10CM"]
        if not billing_code:
            billing_code = "N/A"

        print("\n".join(str(m) for m in matches))
        # result = [m for m in matches if m["ontology"] == "SNOMEDCT_US"][0]
        return {
            "cui": result['cui'],
            "snomed_code": snomed_code,
            "billing_code": billing_code,
            "name": result['name']
        }

# snomed_code = "363455001"  # Example SNOMED code for diabetes
snomed_code = "lung cancer"  # Example SNOMED code for diabetes mellitus
x = asyncio.run(get_billing_codes_from_snomed(snomed_code))  # Replace with actual SNOMED code
print(x)