import json
import httpx
import asyncio

BASE = "http://localhost:8000"  # or wherever your API is running

async def get_codes_from_natural_language(natural_language_query):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/cuis", params={"query": natural_language_query})
        r.raise_for_status()
        matches = r.json()
        result = [m for m in matches["cuis"] if m["language_code"] == "ENG"][0]
        print(result)

        r = await client.get(f"{BASE}/code-map/", params={"cui": result['cui']})
        r.raise_for_status()
        matches = r.json()['code_maps']
        snomed_list = [m for m in matches if m["sab"] == "SNOMEDCT_US"]
        snomed_code = snomed_list[0]['code'] if snomed_list else "N/A"
        billing_list = [m["code"] for m in matches if m["sab"] == "ICD10CM"]
        billing_code = billing_list[0] if billing_list else "N/A"
        # result = [m for m in matches if m["ontology"] == "SNOMEDCT_US"][0]
        return {
            "cui": result['cui'],
            "snomed_code": snomed_code,
            "billing_code": billing_code,
            "name": result['name']
        }


# Write a function to get the ICDM10CM code from a SNOMED code
async def get_icd10cm_from_snomed(snomed_code):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/snomed_to_icd10cm", params={"code": snomed_code})
        r.raise_for_status()
        return r.json()

# snomed_code = "363455001"  # Example SNOMED code for diabetes
nl_query = "malignant neoplasm of adrenal gland"  # Example natural language query for lung cancer
print(f"Getting SNOMED code from natural language query: {nl_query}...")
x = asyncio.run(get_codes_from_natural_language(nl_query))  # Replace with actual SNOMED code
print(x)

snomed_code = x['snomed_code']
print(f"Getting ICD10CM codes for SNOMED code: {snomed_code}...")
icd10cm_result = asyncio.run(get_icd10cm_from_snomed(snomed_code))
print(f"ICD10CM codes for SNOMED code {snomed_code}:")
print(json.dumps(icd10cm_result, indent=2))