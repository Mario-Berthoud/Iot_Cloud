import os
import socket
import urllib3
import logging
from typing import Callable, Any, List
from fastapi import FastAPI

logger = logging.getLogger("fastapi_cli")


class LocalGateway(FastAPI):
    """
    Child class of FastAPI to include custom deployment methods so REST API
    endpoints are registered transparently. This class follows the same signature
    as FastAPI, except it adds one more parameter to allow for mocking functionality.

    As it extendes FastAPI, the usage also remains the same:

    ```python
    from gateway import LocalGateway

    app = LocalGateway()

    app.deploy(fn, 'My-Func', 'My-Event', 'POST')
    ```

    :param mock: Indicates if remote calls must be mocked
    """

    def __init__(self, mock: bool = False, *args, **kwargs):
        super(LocalGateway, self).__init__(*args, **kwargs)
        self.local_ip = None
        self.local_port = None
        self.mock = mock
        self.scheduler = os.environ.get("SCH_SERVICE_NAME", "localhost:8080")
        if self.scheduler is None and not mock:
            raise ValueError(
                "SCH_SERVICE_NAME should be given as an environment variable")
        self.__get_hostname()

    def deploy(self, cb: Callable[..., Any], name: str, evts: List[str] | str,  method: str = "GET", path: str = None):
        """
        Handles dynamically registration of endpoints within the server and
        scheduler

        :param cb: REST API endpoint handler
        :param name: Function name to be given for the scheduler
        :param evts: EventRequests the function must subscribe
        :param method: Type of HTTP Method the SIF-edge's dispatcher must use to invoke the cb
        :param path: By default, `/api/cb.__name__` is used, this method overrides the `cb.__name__`
        """
        endpoint = path or f"/api/{cb.__name__}"
        if not endpoint.startswith("/api"):
            endpoint = "/api/" + \
                (endpoint[1:] if endpoint.startswith("/") else endpoint)

        self.add_api_route(
            endpoint, cb, methods=[method.upper()])

        self.openapi_schema = None
        self.setup()

        endpoint = f"{self.local_ip}:{self.local_port}{endpoint}"
        logger.info(f"Registering the endpoint {endpoint} to {self.scheduler}")

        url = f"{self.scheduler}/api/function"
        if not self.mock:
            evts = evts if isinstance(evts, list) else [evts]
            try:
                http = urllib3.PoolManager()
                res = http.request('POST', url, json=dict(
                    name=name, url=endpoint, subs=evts, method=method.upper()), retries=urllib3.Retry(5))
                if res.status >= 300:
                    logger.error(
                        f"Failure registering function with the scheduler because {res.reason}")
            except Exception as err:
                logger.error("Failure during HTTP request")
                logger.error(err)
        logger.info(
            f"Registered endpoint {endpoint} for {cb.__name__}")

    def __get_hostname(self):
        is_k8s = os.environ.get("KUBERNETES_SERVICE_PORT", None) is not None

        if is_k8s:
            hostname = os.environ.get("HOSTNAME").split("-")[:-2]
            hostname = "_".join(hostname)
            host = f"{hostname.upper()}_SERVICE_HOST"
            port = f"{hostname.upper()}_SERVICE_PORT"
            logger.info("Generating environment for k8s deployment")
            self.local_ip = os.environ[host]
            self.local_port = os.environ[port]
            return

        hostname = socket.gethostname()
        self.local_ip = socket.gethostbyname(hostname)
        logger.warning("Defaulting to port 8000...")
        self.local_port = "8000"
