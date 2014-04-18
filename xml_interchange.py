#!/usr/bin/env python
import xml.etree.ElementTree as ET
from urlparse import urlparse, urljoin
import glob
import os
import os.path as osp
import httplib
import hashlib

VIDEO_DOMAIN = urlparse("http://logc.curiousercreative.com")
VIDEO_REPOSITORY = "/media/offline/"
CHUNK_SIZE = 1024

def checksum_checks_out(http_connection, file_basename, local_file_path):
  path, ext = osp.splitext(file_basename)
  remote_file_url = osp.join(VIDEO_REPOSITORY, "%s.md5" % path)
  http_connection.request("GET", remote_file_url)
  response = http_connection.getresponse()
  remote_checksum = response.read().split(' ')[0]

  with open(local_file_path, 'r') as f:
    local_checksum = hashlib.md5(f.read()).hexdigest()

  return local_checksum == remote_checksum

def download_remote_file(http_connection, file_basename, local_file_path):
  remote_file_url = osp.join(VIDEO_REPOSITORY, file_basename)
  http_connection.request("GET", remote_file_url)
  response = http_connection.getresponse()

  # Write to a file CHUNK_SIZE bytes at a time
  # TODO: some visuals here?
  with open(local_file_path, 'wb') as f:
    data_chunk = response.read(CHUNK_SIZE)
    while data_chunk:
      f.write(data_chunk)
      data_chunk = response.read(CHUNK_SIZE)


def check_for_remote_file(http_connection, file_basename):
  remote_file_url = osp.join(VIDEO_REPOSITORY, file_basename)
  http_connection.request("HEAD", remote_file_url)
  response = http_connection.getresponse()
  headers = dict(response.getheaders())
  response.read()
  # we have to check content type because the server is configured to redirect to an app on 404
  return (response.status == 200 and (headers["content-type"] == "text/plain" or headers["content-type"] == "video/quicktime"))

def build_local_url(file_url):
  return urlparse(osp.join(os.getcwd(), url_basename(file_url)), scheme="file")

def url_basename(file_url):
  return osp.basename(file_url.path)

def main():
  # There should only be one xml file in this directory
  project_xml = glob.glob("*.xml")[0]

  # Parse that xml tree
  tree = ET.parse(project_xml)
  root = tree.getroot()

  # Connect to the video repository (we don't wanna do this a million times)
  video_domain_connection = httplib.HTTPConnection(VIDEO_DOMAIN.netloc)

  # Now we need to find all instances of <pathurl /> tags and replace their innerds
  for pathurl in root.iter("pathurl"):
    # Replace the path in the xml document
    remote_file_url = urlparse(pathurl.text)
    local_file_url = build_local_url(remote_file_url)
    pathurl.text = local_file_url.geturl()

    # Check to see if we have that file locally.
    file_basename = url_basename(local_file_url)
    remote_file = urljoin(VIDEO_REPOSITORY, url_basename(local_file_url))
    if not os.path.exists(file_basename):
      # Check to see if it's on the remote server
      if not check_for_remote_file(video_domain_connection,file_basename):
        print "File %s is not on the remote server" % file_basename

      # Download it from a remote server
      else:
        download_remote_file(video_domain_connection, file_basename, local_file_url.path)
        if not checksum_checks_out(video_domain_connection, file_basename, local_file_url.path):
          print "File %s was corrupted. Deleting." % local_file_url.path
          os.remove(local_file_url.path)
        else:
          print "Successfully downloaded and verified %s" % local_file_url.path

  # Finally write the xml document
  tree.write(project_xml)





if __name__ == "__main__":
  main()
