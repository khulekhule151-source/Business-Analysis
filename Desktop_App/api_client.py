import requests

class APIClient:
    def __init__(self, base_url): self.base_url=base_url.rstrip('/'); self.token=None
    def headers(self): return {"Authorization":f"Bearer {self.token}"} if self.token else {}
    def health(self): return requests.get(self.base_url+'/health',timeout=10)
    def login(self,email,password):
        r=requests.post(self.base_url+'/api/auth/login',json={"email":email,"password":password},timeout=20); r.raise_for_status(); data=r.json(); self.token=data['access_token']; return data
    def get(self,path,**kwargs):
        r=requests.get(self.base_url+path,headers=self.headers(),timeout=30,**kwargs); r.raise_for_status(); return r.json()
    def post_file(self,path,file_path):
        with open(file_path,'rb') as f:
            r=requests.post(self.base_url+path,headers=self.headers(),files={'file':(file_path.split('/')[-1],f)},timeout=180)
        r.raise_for_status(); return r.json()
    def post_json(self,path,payload):
        r=requests.post(self.base_url+path,headers=self.headers(),json=payload,timeout=30); r.raise_for_status(); return r.json()
    def patch_json(self,path,payload):
        r=requests.patch(self.base_url+path,headers=self.headers(),json=payload,timeout=30); r.raise_for_status(); return r.json()
    def delete(self,path):
        r=requests.delete(self.base_url+path,headers=self.headers(),timeout=30); r.raise_for_status(); return r.json()
