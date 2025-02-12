# 🏥 UMLS Concept Lookup API

## Using the EC2 on 52.43.228.165
### 🚀 **Quick Start: Search for Medical Terms**
If using the preset UMLS server on [ec2 instance](https://us-west-2.console.aws.amazon.com/ec2/home?region=us-west-2#InstanceDetails:instanceId=i-02871ce2788a7a8c2) on IP 52.43.228.165, your-ec2-public-ip = 52.43.228.165. 
Ensure you are on the Geneial VPN to be able to connect. 
Ensure that the EC2 is on while in use and off when not in use (it seems to cost ~50c an hour)!!

UPDATE 2/7: When the instance is on, the UMLS server should automatically turn on. The server will shut down automatically at midnight ET every night.  

To run the API from the pre-installed EC2 instance: 
First, ssh into the  EC2 (ask Julie for .pem file), then run the app.
```sh
ssh -i "umls-server.pem" ec2-user@ec2-52-43-228-165.us-west-2.compute.amazonaws.com
cd umls-server/umls_api
uvicorn app:app --host 0.0.0.0 --port 8000
```

To search for related to a term (e.g. "cancer") in a specific ontology (e.g. "HPO" or "NCI"):
```sh
curl "http://your-ec2-public-ip:8000/terms?search=cancer&ontology=HPO"

```
OR you can use the python requests library. 

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
| `GET`  | `/terms?search={term}&ontology={ontology}` | Search for a term (Default: `HPO`) |
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
- **API not accessible?** Make sure EC2 is on and open port **8000** in your EC2 **Security Group**.  
- **No results found?** Ensure your **ontology (`HPO`, `NCI`, etc.)** is correct.  
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

