import os
import json
import time
import socket
import urllib2
import logging
import requests
import lxml.etree as etree
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

# Avoid hangs when systems are unreachable:
TIMEOUT = 10
socket.setdefaulttimeout(TIMEOUT)


class HDFSCollector(object):

    def collect(self):
        try:
            stats = self.get_hdfs_status(os.environ.get('HDFS_HEALTH_PAGE'))
            service_label = os.environ.get("HDFS_SERVICE_LABEL","production")

            urb = GaugeMetricFamily(
                'hdfs_under_replicated_block_count',
                'Total number of under-replicated blocks',
                labels=['service'])
            val = stats.get('under-replicated-blocks', None)
            if val is not None:
                urb.add_metric([service_label], val)
                yield urb

            hup = GaugeMetricFamily(
                'hdfs_used_percent',
                'HDFS used space as a percentage',
                labels=['service'])
            val = stats.get('percent-used', None)
            if val is not None:
                hup.add_metric([service_label], val)
                yield hup

            hnc = GaugeMetricFamily(
                'hdfs_node_count',
                'HDFS node counts',
                labels=['service','status'])
            hnc.add_metric([service_label, 'live'], stats.get('live-nodes', 0))
            hnc.add_metric([service_label, 'dead'], stats.get('dead-nodes', 0))
            yield hnc

        except Exception as e:
            logger.exception("FAILED")

    def get_hdfs_status(self, url):
        state = {}
        logger.info("Getting status for hdfs %s" % (url))
        r = requests.get(url, timeout=(TIMEOUT, TIMEOUT))
        state['status'] = "%s" % r.status_code
        if r.status_code / 100 == 2:
            tree = etree.fromstring(r.text, etree.HTMLParser())
            percent = tree.xpath("//div[@id='dfstable']//tr[5]/td[3]")[0].text
            percent = percent.replace(" ", "")
            state['percent-used'] = float(percent.replace("%",""))
            state['remaining'] = tree.xpath("//div[@id='dfstable']//tr[4]/td[3]")[0].text.replace(" ", "")
            underr = int(tree.xpath("//div[@id='dfstable']//tr[10]/td[3]")[0].text)
            if underr > 0:
                logger.warning("Got under-rep-blocks > 0 from: %s" % r.text)
            state['under-replicated-blocks'] = underr
            state['live-nodes'] = int(tree.xpath("//div[@id='dfstable']//tr[7]/td[3]")[0].text)
            state['dead-nodes'] = int(tree.xpath("//div[@id='dfstable']//tr[8]/td[3]")[0].text)
        else:
            logger.error("That went wrong! Status %i:\n%s" % (r.status_code, r.text))

        return state


if __name__ == "__main__":
    REGISTRY.register(HDFSCollector())
    start_http_server(9118)
    while True: time.sleep(1)