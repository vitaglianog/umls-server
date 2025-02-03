# 🏥 UMLS Concept Lookup API

### 🚀 **Quick Start: Search for Medical Terms**
If using the preset UMLS server on ec2 instance on IP 52.43.228.165, your-ec2-public-ip = 52.43.228.165 

To search for HPO or NCIT concepts related to a term:
```sh
curl "http://your-ec2-public-ip:8000/terms?search=cancer&ontology=HPO"

```
Example Response:
```json
{
  "results": [
    {
      "code": "HP:0002896",
      "term": "Liver cancer",
      "description": "A primary or metastatic malignant neoplasm that affects the liver."
    }
  ]
}
```

To fetch details for a specific **CUI**:
```sh
curl "http://your-ec2-public-ip:8000/concepts/HP:0002896"
```

---

## 🌐 **API Endpoints**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/terms?search={term}&ontology={ontology}` | Search for a term (Default: `HPO` or `NCI`) |
| `GET`  | `/concepts/{cui}` | Get concept details by CUI |

---

## 📌 **Installation**
1. **Clone the repository & install dependencies**  
   ```sh
   git clone https://github.com/yourusername/umls-api.git
   cd umls-api
   pip install -r requirements.txt
   ```

2. **Set up environment variables** in `.env`:
   ```ini
   DB_HOST=your-db-host
   DB_USER=your-db-user
   DB_PASSWORD=your-db-password
   DB_NAME=your-db-name
   ```

3. **Run the API**
   ```sh
   cd umls-server/umls_api
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

---

## 🛠 **Troubleshooting**
- **API not accessible?** Open port **8000** in your EC2 **Security Group**.  
- **No results found?** Ensure your **ontology (`HPO`, `NCIT`)** is correct.  
- **API stops when logging out?** Run:
  ```sh
  nohup uvicorn app:app --host 0.0.0.0 --port 8000 > umls_api.log 2>&1 &
  ```

---

## 🤝 **Contributing**
1. Fork the repo & create a new branch (`feature-name`).
2. Commit changes (`git commit -m "Added feature"`).
3. Push & open a pull request.

---

## 📜 **License**
MIT License

---

🚀 Now you're ready to query UMLS with ease!

