# 🏥 UMLS 2025AA Release Analysis

## 📋 Release Information

- **Version**: 2025AA (Spring 2025 Base Release)
- **Release Date**: May 5, 2025 (20250505)
- **Build Date**: April 28, 2025 (2025_04_28_13_33_05)
- **Description**: Base Release for Spring 2025
- **MMSYS Version**: MMSYS-2025AA-20250307
- **LVG Version**: 2025

## 📁 Directory Structure

```
umls-data/2025AA/
├── Copyright_Notice.txt (11KB)
├── README.txt (494B)
└── META/
    ├── Core Data Files (.RRF)
    ├── Official Scripts
    ├── Configuration Files
    └── Language-specific Files
```

## 📊 Core Data Files Analysis

### Primary UMLS Tables

| File | Size | Purpose | Status |
|------|------|---------|--------|
| **MRCONSO.RRF** | 2.1GB | Main concepts and sources | ✅ Available |
| **MRDEF.RRF** | 124MB | Concept definitions | ✅ Available |
| **MRHIER.RRF** | 5.5GB | Hierarchical relationships | ✅ Available |
| **MRREL.RRF** | 5.7GB | Concept relationships | ✅ Available |
| **MRSAT.RRF** | 8.8GB | Concept attributes | ✅ Available |
| **MRSTY.RRF** | 205MB | Semantic types | ✅ Available |

### Additional Data Files

| File | Size | Purpose |
|------|------|---------|
| **MRXNS_ENG.RRF** | 1013MB | English normalized strings |
| **MRXNW_ENG.RRF** | 1.9GB | English normalized words |
| **MRXW_ENG.RRF** | 1.8GB | English word index |
| **MRAUI.RRF** | 18MB | Atom unique identifiers |
| **MRCUI.RRF** | 74MB | Concept unique identifiers |
| **MRMAP.RRF** | 138MB | Mapping information |
| **MRSMAP.RRF** | 35MB | Simple maps |

### Multi-language Support

The release includes word indexes for **24 languages**:

| Language | File | Size |
|----------|------|------|
| Arabic | MRXW_ARA.RRF | 16MB |
| Chinese | MRXW_CHI.RRF | 28MB |
| Czech | MRXW_CZE.RRF | 23MB |
| Dutch | MRXW_DUT.RRF | 70MB |
| English | MRXW_ENG.RRF | 1.8GB |
| French | MRXW_FRE.RRF | 105MB |
| German | MRXW_GER.RRF | 38MB |
| Greek | MRXW_GRE.RRF | 52MB |
| Italian | MRXW_ITA.RRF | 52MB |
| Japanese | MRXW_JPN.RRF | 17MB |
| Korean | MRXW_KOR.RRF | 22MB |
| Polish | MRXW_POL.RRF | 26MB |
| Portuguese | MRXW_POR.RRF | 65MB |
| Russian | MRXW_RUS.RRF | 54MB |
| Spanish | MRXW_SPA.RRF | 509MB |
| Swedish | MRXW_SWE.RRF | 15MB |
| And 8 more... | | |

## 🛠️ Official UMLS Scripts Available

### MySQL Scripts
- **mysql_tables.sql** (28KB, 1048 lines) - Complete table creation
- **mysql_indexes.sql** (3.4KB, 148 lines) - Performance indexes
- **populate_mysql_db.sh** (2.7KB, 81 lines) - Data loading script
- **populate_mysql_db.bat** (2.7KB, 74 lines) - Windows version

### Oracle Scripts
- **oracle_tables.sql** (16KB, 656 lines) - Oracle table creation
- **oracle_indexes.sql** (5.6KB, 223 lines) - Oracle indexes
- **populate_oracle_db.sh** (10KB, 237 lines) - Oracle loading script
- **populate_oracle_db.bat** (11KB, 236 lines) - Windows Oracle version

## 📈 Estimated Database Size

Based on file sizes and typical index overhead:

| Component | Raw Data | With Indexes | Total |
|-----------|----------|--------------|-------|
| MRCONSO | 2.1GB | ~1GB | ~3.1GB |
| MRHIER | 5.5GB | ~2GB | ~7.5GB |
| MRREL | 5.7GB | ~2GB | ~7.7GB |
| MRSAT | 8.8GB | ~3GB | ~11.8GB |
| Other core tables | ~500MB | ~200MB | ~700MB |
| **Total Estimate** | **~22.6GB** | **~8.2GB** | **~30.8GB** |

## 🏗️ Database Schema Compliance

The release includes official schemas that are:
- **Character Set**: UTF-8
- **Collation**: utf8_unicode_ci
- **Engine**: InnoDB (recommended)
- **Field Terminators**: Pipe (|) delimited
- **Line Terminators**: Unix newlines (\n)

## 🌐 Supported Ontologies & Vocabularies

Based on the UMLS structure, this release likely includes:

### Major Medical Ontologies
- **HPO** - Human Phenotype Ontology
- **SNOMEDCT_US** - SNOMED Clinical Terms (US Edition)
- **NCI** - National Cancer Institute Thesaurus
- **MSH** - Medical Subject Headings (MeSH)
- **ICD10CM** - International Classification of Diseases, 10th Revision
- **ICD10PCS** - ICD-10 Procedure Coding System
- **CPT** - Current Procedural Terminology
- **LOINC** - Logical Observation Identifiers Names and Codes

### Specialized Vocabularies
- **DRUGBANK** - Drug and drug target database
- **RXNORM** - Clinical drug nomenclature
- **GO** - Gene Ontology
- **OMIM** - Online Mendelian Inheritance in Man
- **And 100+ more vocabularies**

## ⚡ Performance Expectations

### Loading Times (estimated on modern hardware)
- **MRCONSO**: 15-30 minutes
- **MRDEF**: 2-5 minutes
- **MRHIER**: 45-90 minutes
- **MRREL**: 60-120 minutes
- **MRSAT**: 2-4 hours
- **Total Core Load**: 3-6 hours
- **Index Creation**: 30-60 minutes

### Query Performance
With proper indexing:
- **Simple term searches**: < 100ms
- **Complex relationship queries**: 200ms - 2s
- **Hierarchical traversals**: 100ms - 1s
- **Cross-ontology mappings**: 500ms - 5s

## 🎯 Loading Recommendations

### Minimal Setup (Core functionality)
Load these tables for basic UMLS functionality:
1. **MRCONSO** - Essential for all operations
2. **MRDEF** - Required for definitions
3. **MRHIER** - Needed for hierarchy operations
4. **MRREL** - Required for relationship queries

**Total Size**: ~19GB, **Load Time**: ~2-4 hours

### Full Setup (Complete functionality)
Add these for full UMLS capabilities:
5. **MRSTY** - Semantic type information
6. **MRSAT** - Detailed attributes

**Total Size**: ~31GB, **Load Time**: ~4-7 hours

### Specialized Features
For specific use cases, consider:
- **MRXW_ENG.RRF** - English word indexing
- **MRMAP.RRF** - Cross-ontology mappings
- **Language-specific MRXW_*.RRF** - Multi-language support

## 🔧 Custom Loading Script Features

The provided `load_umls_2025aa.sh` script:

### ✅ What it does:
- Uses official UMLS table schemas
- Loads core tables with proper data types
- Creates optimized indexes
- Provides progress feedback
- Validates data loading
- Works with Docker MySQL setup

### 🎯 Optimizations:
- Uses InnoDB engine for better performance
- Creates selective indexes for API queries
- Handles large file loading efficiently
- Provides rollback capability
- Includes data validation tests

## 🚀 Next Steps

1. **Start MySQL Container**:
   ```bash
   docker compose up -d mysql
   ```

2. **Load UMLS 2025AA Data**:
   ```bash
   ./scripts/load_umls_2025aa.sh
   ```

3. **Start API Service**:
   ```bash
   docker compose up -d umls-api
   ```

4. **Test API**:
   ```bash
   curl "http://localhost:8000/terms?search=diabetes&ontology=HPO"
   ```

## 📚 Resources

- **UMLS Documentation**: https://www.ncbi.nlm.nih.gov/books/NBK9684/
- **Release Notes**: https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/notes.html
- **Vocabulary List**: https://www.nlm.nih.gov/research/umls/sourcereleasedocs/index.html

---

**🎉 You have access to the latest, most comprehensive UMLS release available!** 