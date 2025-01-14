import sh
import pytest
import requests
import yaml
from .utils import asyncify, retry_async_with_timeout
from .logger import log


def get_pod_yaml():
    out = sh.kubectl.get("po", o="yaml", selector="app=hello-world")
    return yaml.safe_load(out.stdout.decode())


def get_svc_yaml():
    out = sh.kubectl.get("svc", o="yaml", selector="app=hello-world")
    return yaml.safe_load(out.stdout.decode())


async def is_pod_running():
    pod = get_pod_yaml()

    try:
        phase = pod["items"][0]["status"]["phase"]
    except IndexError:
        # Pod is not created yet
        return False

    if "Running" in phase:
        return True
    # Pod has not fully come up yet
    return False


async def is_pod_cleaned():
    pod = get_pod_yaml()
    if not pod["items"]:
        return True
    return False


async def setup_svc(svc_type):
    # Create Deployment
    sh.kubectl.create(
        "deployment",
        "hello-world",
        image="rocks.canonical.com/cdk/google-samples/node-hello:1.0",
    )
    sh.kubectl.set("env", "deployment/hello-world", "PORT=50000")

    # Create Service
    sh.kubectl.expose(
        "deployment",
        "hello-world",
        type=f"{svc_type}",
        name="hello-world",
        protocol="TCP",
        port=80,
        target_port=50000,
    )

    # Wait for Pods to stabilize
    await retry_async_with_timeout(
        is_pod_running, (), timeout_msg="Pod(s) failed to stabilize before timeout"
    )


async def cleanup():
    sh.kubectl.delete("deployment", "hello-world")
    sh.kubectl.delete("service", "hello-world")
    await retry_async_with_timeout(
        is_pod_cleaned, (), timeout_msg="Pod(s) failed to clean before timeout"
    )


@pytest.mark.asyncio
async def test_nodeport_service_endpoint():
    """Create k8s Deployement and NodePort service, send request to NodePort"""

    try:
        await setup_svc("NodePort")

        # Grab the port
        svc = get_svc_yaml()
        port = svc["items"][0]["spec"]["ports"][0]["nodePort"]

        # Grab Pod IP
        pod = get_pod_yaml()
        ip = pod["items"][0]["status"]["hostIP"]

        # Build the url
        set_url = f"http://{ip}:{port}"
        html = await asyncify(requests.get)(set_url)

        assert "Hello Kubernetes!" in html.content.decode()

    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_clusterip_service_endpoint(model):
    """Create k8s Deployement and ClusterIP service, send request to ClusterIP
    from each kubernetes master and worker
    """

    try:
        await setup_svc("ClusterIP")

        # Grab ClusterIP from svc
        pod = get_svc_yaml()
        ip = pod["items"][0]["spec"]["clusterIP"]

        # Build the url
        set_url = f"http://{ip}:80"
        cmd = f'curl -vk --noproxy "{ip}" {set_url}'

        # Curl the ClusterIP from each kubernetes master and worker
        master = model.applications["kubernetes-master"]
        worker = model.applications["kubernetes-worker"]
        nodes_lst = master.units + worker.units
        for unit in nodes_lst:
            action = await unit.run(cmd)
            try:
                assert "Hello Kubernetes!" in action.results.get("Stdout", "")
            except AssertionError as e:
                log(f"connection on {unit} failed")
                raise e

    finally:
        await cleanup()
