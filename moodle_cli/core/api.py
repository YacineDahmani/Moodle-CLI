from typing import Any, Dict, List, Optional
import requests
from moodle_cli.core.config import Config


class MoodleError(Exception):
    pass


class MoodleAuthError(MoodleError):
    pass


class MoodleAPIError(MoodleError):
    def __init__(self, message: str, errorcode: Optional[str] = None):
        super().__init__(message)
        self.errorcode = errorcode


class MoodleClient:
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MoodleCLI/1.0"})
        self.token = config.token
        self.site_info: Optional[Dict[str, Any]] = None

    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> str:
        username = username or self.config.username
        password = password or self.config.password

        if not self.config.url:
            raise MoodleAuthError("Moodle site URL is not configured.")

        if not username or not password:
            raise MoodleAuthError("Missing username or password.")

        token_url = f"{self.config.url}/login/token.php"
        params = {
            "username": username,
            "password": password,
            "service": "moodle_mobile_app",
        }

        try:
            resp = self.session.get(token_url, params=params, timeout=20)
            data = resp.json()
        except requests.RequestException as e:
            raise MoodleError(f"Network error during authentication: {e}")
        except ValueError:
            raise MoodleError(f"Invalid JSON received from {token_url}")

        if "token" in data:
            self.token = data["token"]
            self.config.token = self.token
            return self.token
        elif "error" in data:
            error_msg = data.get("error", "Unknown error")
            error_code = data.get("errorcode", "")
            raise MoodleAuthError(f"{error_msg} (code: {error_code})" if error_code else error_msg)
        else:
            raise MoodleAuthError(f"Unexpected authentication response: {data}")

    def ensure_authenticated(self) -> None:
        if not self.token:
            self.authenticate()

    def call(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self.ensure_authenticated()

        url = f"{self.config.url}/webservice/rest/server.php"
        query_params = {
            "wstoken": self.token,
            "wsfunction": function_name,
            "moodlewsrestformat": "json",
        }
        if params:
            query_params.update(params)

        try:
            resp = self.session.get(url, params=query_params, timeout=30)
            data = resp.json()
        except requests.RequestException as e:
            raise MoodleError(f"API connection error for {function_name}: {e}")
        except ValueError:
            raise MoodleError(f"Invalid JSON returned from API call: {function_name}")

        if isinstance(data, dict):
            if "exception" in data or "errorcode" in data:
                if data.get("errorcode") in ("invalidtoken", "accessexception"):
                    self.token = ""
                    if self.config.username and self.config.password:
                        self.authenticate()
                        query_params["wstoken"] = self.token
                        retry_resp = self.session.get(url, params=query_params, timeout=30)
                        return retry_resp.json()
                raise MoodleAPIError(data.get("message", "API Error"), errorcode=data.get("errorcode"))

        return data

    def get_site_info(self) -> Dict[str, Any]:
        if not self.site_info:
            self.site_info = self.call("core_webservice_get_site_info")
        return self.site_info

    def get_courses(self) -> List[Dict[str, Any]]:
        info = self.get_site_info()
        userid = info["userid"]
        courses = self.call("core_enrol_get_users_courses", {"userid": userid})
        return courses if isinstance(courses, list) else []

    def get_course_contents(self, course_id: int) -> List[Dict[str, Any]]:
        contents = self.call("core_course_get_contents", {"courseid": course_id})
        return contents if isinstance(contents, list) else []
