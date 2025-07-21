import json
import httpx
import asyncio

BASE = "http://localhost:8000"  # or wherever your API is running

async def get_codes_from_natural_language(natural_language_query):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/cuis", params={"query": natural_language_query})
        r.raise_for_status()
        matches = r.json()
        results = [m for m in matches["cuis"] if m["language_code"] == "ENG"]

        codes = {m['cui']: m for m in results}
        snomed_codes = {}
        billing_codes = {}
        for key, cui in codes.items():
            r = await client.get(f"{BASE}/code-map/", params={"cui": key})
            r.raise_for_status()
            matches = r.json()['code_maps']
            for m in matches:
                if m['sab'] == 'SNOMEDCT_US':
                    snomed_codes[key] = m
                    codes[key]['snomed'] = m
                elif m['sab'] == 'ICD10CM':
                    billing_codes[key] = m
                    codes[key]['icd10m'] = m
            
        # Retain only CUI codes that have both SNOMED and ICD10CM codes
        return_codes = []
        for key in list(codes.keys()):
            if key in snomed_codes and key in billing_codes:
                return_codes.append({
                    "cui": key,
                    "cui_name": codes[key]['name'],
                    "snomed_code": snomed_codes[key]['code'],
                    "snomed_name": snomed_codes[key]['name'],
                    "icd10cm_code": billing_codes[key]['code'],
                    "icd10cm_name": billing_codes[key]['name']
                })

        return return_codes
    


# Write a function to get the ICDM10CM code from a SNOMED code
async def get_icd10cm_from_snomed(snomed_code):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/snomed_to_icd10cm", params={"code": snomed_code})
        r.raise_for_status()
        return r.json()


# Example usage:

# snomed_code = "363455001"  # Example SNOMED code for diabetes
nl_query = "pleural effusion"  # Example natural language query for lung cancer
x = asyncio.run(get_codes_from_natural_language(nl_query))  # Replace with actual SNOMED code

print(f"Getting codes from natural language query: {nl_query}...")
for disease in x:
    print("CUI name:", disease['cui_name'])
    print("\tSNOMED code:", disease['snomed_code'])
    print("\tICD10CM code:", disease['icd10cm_code'])
    print()