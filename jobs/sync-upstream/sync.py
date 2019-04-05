""" sync repo script
"""
import sh
import os
import uuid
from pathlib import Path
from sdk import utils

repos = [
    ["charmed-kubernetes/interface-aws-integration.git", "https://github.com/juju-solutions/interface-aws-integration.git"],
    ["charmed-kubernetes/interface-azure-integration.git", "https://github.com/juju-solutions/interface-azure-integration.git"],
    ["charmed-kubernetes/interface-dockerhost.git", "https://github.com/juju-solutions/interface-dockerhost.git"],
    ["charmed-kubernetes/interface-docker-registry.git", "https://github.com/juju-solutions/interface-docker-registry.git"],
    ["charmed-kubernetes/interface-etcd.git", "https://github.com/juju-solutions/interface-etcd.git"],
    ["charmed-kubernetes/interface-etcd-proxy.git", "https://github.com/juju-solutions/interface-etcd-proxy.git"],
    ["charmed-kubernetes/interface-gcp-integration.git", "https://github.com/juju-solutions/interface-gcp-integration.git"],
    ["charmed-kubernetes/charm-interface-hacluster.git", "https://github.com/openstack/charm-interface-hacluster.git"],
    ["charmed-kubernetes/interface-http.git", "https://github.com/juju-solutions/interface-http.git"]
    ["charmed-kubernetes/interface-juju-info.git", "https://github.com/juju-solutions/interface-juju-info.git"],
    ["charmed-kubernetes/interface-kube-control.git", "https://github.com/juju-solutions/interface-kube-control.git"],
    ["charmed-kubernetes/interface-kube-dns.git", "https://github.com/juju-solutions/interface-kube-dns.git"],
    ["charmed-kubernetes/interface-kubernetes-cni.git", "https://github.com/juju-solutions/interface-kubernetes-cni.git"],
    ["charmed-kubernetes/interface-mount.git", "https://github.com/juju-solutions/interface-mount.git"],
    ["charmed-kubernetes/nrpe-external-master-interface.git", "https://github.com/cmars/nrpe-external-master-interface.git"],
    ["charmed-kubernetes/interface-openstack-integration.git", "https://github.com/juju-solutions/interface-openstack-integration.git"],
    ["charmed-kubernetes/charm-interface-peer-discovery.git", "https://github.com/tbaumann/charm-interface-peer-discovery.git"],
    ["charmed-kubernetes/interface-public-address.git", "https://github.com/juju-solutions/interface-public-address.git"],
    ["charmed-kubernetes/interface-sdn-plugin.git", "https://github.com/juju-solutions/interface-sdn-plugin.git"],
    ["charmed-kubernetes/interface-tls-certificates.git", "https://github.com/juju-solutions/interface-tls-certificates.git"],
    ["charmed-kubernetes/charm-interface-vault-kv.git", "https://github.com/openstack-charmers/charm-interface-vault-kv.git"],
    ["charmed-kubernetes/interface-vsphere-integration.git", "https://github.com/juju-solutions/interface-vsphere-integration.git"],
    ["charmed-kubernetes/layer-basic.git", "https://github.com/juju-solutions/layer-basic.git"],
    ["charmed-kubernetes/layer-cdk-service-kicker.git", "https://github.com/juju-solutions/layer-cdk-service-kicker.git"],
    ["charmed-kubernetes/layer-debug.git", "https://github.com/juju-solutions/layer-debug.git"],
    ["charmed-kubernetes/layer-docker.git", "https://github.com/juju-solutions/layer-docker.git"],
    ["charmed-kubernetes/layer-hacluster.git", "https://github.com/juju-solutions/layer-hacluster.git"],
    ["charmed-kubernetes/layer-metrics.git", "https://github.com/CanonicalLtd/layer-metrics.git"],
    ["charmed-kubernetes/juju-layer-nginx.git", "https://github.com/battlemidget/juju-layer-nginx.git"],
    ["charmed-kubernetes/layer-options.git", "https://github.com/juju-solutions/layer-options.git"],
    ["charmed-kubernetes/layer-status.git", "https://github.com/juju-solutions/layer-status.git"],
    ["charmed-kubernetes/layer-tls-client.git", "https://github.com/juju-solutions/layer-tls-client.git"],
    ["charmed-kubernetes/layer-vault-kv.git", "https://github.com/juju-solutions/layer-vault-kv.git"],
    ["charmed-kubernetes/layer-vaultlocker.git", "https://github.com/juju-solutions/layer-vaultlocker.git"],
    ["charmed-kubernetes/layer-apt.git", "https://git.launchpad.net/layer-apt"],
    ["charmed-kubernetes/layer-leadership.git", "https://git.launchpad.net/layer-leadership"],
    ["charmed-kubernetes/layer-nagios.git", "https://git.launchpad.net/nagios-layer"],
    ["charmed-kubernetes/layer-snap.git", "https://git.launchpad.net/layer-snap"],
    ["charmed-kubernetes/layer-index.git", "https://github.com/juju/layer-index.git"]
]

new_env = os.environ.copy()

def sync():
    """ Syncs all repos
    """
    for downstream, upstream in repos:
        identifier = str(uuid.uuid4())
        os.makedirs(identifier)
        with sh.cd(identifier):
            sh.git("config", "user.email", 'cdkbot@juju.solutions')
            sh.git("config", "user.name", 'cdkbot')
            sh.git("remote", "add", "upstream", upstream)
            sh.git("fetch", "upstream")
            sh.git("checkout", "master")
            sh.git("merge", "upstream/master")
            sh.git("pull", "--tags", "upstream master")
            sh.git("push", "--tags", f"https://{new_env['CDKBOT_GH']}@github.com/{downstream}", "master")

if __name__ == "__main__":
    sync()