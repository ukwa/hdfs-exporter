FROM python:2.7

# Install the dependencies:
COPY requirements.txt /hdfs_exporter/requirements.txt
RUN cd /hdfs_exporter/ && pip install --no-cache-dir -r requirements.txt

# Install the app:
COPY webapp.py /hdfs_exporter/
COPY setup.py /hdfs_exporter/
COPY README.md /hdfs_exporter/
RUN cd /hdfs_exporter/ && python setup.py install

# Run the stats endpoint
CMD ["python", "/hdfs_exporter/webapp.py"]
