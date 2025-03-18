import os

import requests



class AccessManager:
    """
    Manages access to the API, handling logins and access token storage
    """

    def __init__(
            self,
            email: str,
            password: str
    ):
        self.email = email
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.login()

    def get_bearer_authorization_header(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def login(self):
        response = requests.post(
            f"{os.getenv('VITE_VUE_APP_BASE_URL')}/auth/login",
            json={
                "email": self.email,
                "password": self.password
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]

    def refresh_access_token(self):
        response = requests.post(
            f"{os.getenv('VITE_VUE_APP_BASE_URL')}/auth/refresh-session",
            headers={
                "Authorization": f"Bearer {self.refresh_token}"
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]