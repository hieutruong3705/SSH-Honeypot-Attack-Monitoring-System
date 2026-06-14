import requests
import hashlib

url = 'https://secure.eicar.org/eicar.com'
r = requests.get(url)
file_hash = hashlib.sha256(r.content).hexdigest()
print(f"Eicar hash: {file_hash}")

vt_key = '86d5eb78a976604b0fbdc8d7a692756fa242dbee383688d26dc95306773ed586'
headers = {
    "accept": "application/json",
    "x-apikey": vt_key
}
vt_url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
vt_res = requests.get(vt_url, headers=headers)
print(vt_res.status_code)
print(vt_res.text[:500])
