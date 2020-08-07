#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2020 Battelle Energy Alliance, LLC.  All rights reserved.

import clamd
import hashlib
import malass_client
import os
import re
import requests
import sys
import time

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from collections import Counter
from collections import deque
from collections import defaultdict
from datetime import datetime
from multiprocessing import RawValue
from threading import get_ident
from threading import Lock

###################################################################################################
VENTILATOR_PORT = 5987
SINK_PORT       = 5988

###################################################################################################
# modes for file preservation settings
PRESERVE_QUARANTINED = "quarantined"
PRESERVE_ALL         = "all"
PRESERVE_NONE        = "none"

###################################################################################################
FILE_SCAN_RESULT_FILE = "file"
FILE_SCAN_RESULT_ENGINES = "engines"
FILE_SCAN_RESULT_HITS = "hits"
FILE_SCAN_RESULT_MESSAGE = "message"
FILE_SCAN_RESULT_DESCRIPTION = "description"

###################################################################################################
# the notice field for the signature.log we're writing out mimicing Zeek
ZEEK_SIGNATURE_NOTICE = "Signatures::Sensitive_Signature"

###################################################################################################
# VirusTotal public API
VTOT_MAX_REQS = 4 # maximum 4 public API requests (default)
VTOT_MAX_SEC = 60 # in 60 seconds (default)
VTOT_CHECK_INTERVAL = 0.05
VTOT_URL = 'https://www.virustotal.com/vtapi/v2/file/report'
VTOT_RESP_NOT_FOUND = 0
VTOT_RESP_FOUND = 1
VTOT_RESP_QUEUED = -2

###################################################################################################
# Malass web API
MAL_MAX_REQS = 20 # maximum scanning requests concurrently
MAL_END_OF_TRANSACTION = 'End_of_Transaction'
MAL_SUBMIT_TIMEOUT_SEC = 60
MAL_CHECK_INTERVAL = 1
MAL_RESP_NOT_FOUND = 0
MAL_RESP_FOUND = 1
MAL_RESP_QUEUED = -2

###################################################################################################
# ClamAV Interface
CLAM_MAX_REQS = 8 # maximum scanning requests concurrently, should be <= clamd.conf MaxThreads
CLAM_SUBMIT_TIMEOUT_SEC = 10
CLAM_CHECK_INTERVAL = 0.1
CLAM_ENGINE_ID = 'ClamAV'
CLAM_FOUND_KEY = 'FOUND'

###################################################################################################


# a structure representing the fields of a line of Zeek's signatures.log, and the corresponding string formatting and type definitions
class BroSignatureLine:
  __slots__ = ('ts',  'uid',  'orig_h',  'orig_p',  'resp_h',  'resp_p',  'note',  'signature_id',  'event_message',  'sub_message',  'signature_count',  'host_count')
  def __init__(self, ts='-', uid='-', orig_h='-', orig_p='-', resp_h='-', resp_p='-', note='-', signature_id='-', event_message='-', sub_message='-', signature_count='-', host_count='-'):
    self.ts = ts
    self.uid = uid
    self.orig_h = orig_h
    self.orig_p = orig_p
    self.resp_h = resp_h
    self.resp_p = resp_p
    self.note = note
    self.signature_id = signature_id
    self.event_message = event_message
    self.sub_message = sub_message
    self.signature_count = signature_count
    self.host_count = host_count

  def __str__(self):
    return "\t".join(map(str, [self.ts, self.uid, self.orig_h, self.orig_p, self.resp_h, self.resp_p, self.note, self.signature_id, self.event_message, self.sub_message, self.signature_count, self.host_count]))

  @classmethod
  def signature_format_line(cls):
    return "\t".join(['{'+x+'}' for x in cls.__slots__])

  @classmethod
  def signature_types_line(cls):
    return "\t".join(['time', 'string', 'addr', 'port', 'addr', 'port', 'enum', 'string', 'string', 'string', 'count', 'count'])

# AnalyzerScan
# .provider - a FileScanProvider subclass doing the scan/lookup
# .name - the filename to be scanned
# .submissionResponse - a unique identifier to be returned by the provider with which to check status
class AnalyzerScan:
  __slots__ = ('provider', 'name', 'submissionResponse')
  def __init__(self, provider=None, name=None, submissionResponse=None):
    self.provider = provider
    self.name = name
    self.submissionResponse = submissionResponse

# AnalyzerResult
# .finished - the scan/lookup is no longer executing (whether or not it was successful or returned a "match")
# .success - requesting the status was done successfully (whether or not it was finished)
# .result - the "result" of the scan/lookup, in whatever format is native to the provider
class AnalyzerResult:
  __slots__ = ('finished', 'success', 'result')
  def __init__(self, finished=False, success=False, result=None):
    self.finished = finished
    self.success = success
    self.result = result

# the filename parts used by our Zeek instance for extracted files:
#   source-fuid-uid-time.ext, eg., SSL-FTnzwn4hEPJi7BfzRk-CsRaviydrGyYROuX3-20190402105425.crt
class ExtractedFileNameParts:
  __slots__ = ('source', 'fid', 'uid', 'time', 'ext')
  def __init__(self, source=None, fid=None, uid=None, time=None, ext=None):
    self.source = source
    self.fid = fid
    self.uid = uid
    self.time = time
    self.ext = ext

###################################################################################################
# convenient boolean argument parsing
def str2bool(v):
  if v.lower() in ('yes', 'true', 't', 'y', '1'):
    return True
  elif v.lower() in ('no', 'false', 'f', 'n', '0'):
    return False
  else:
    raise argparse.ArgumentTypeError('Boolean value expected.')

###################################################################################################
# print to stderr
def eprint(*args, **kwargs):
  print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *args, file=sys.stderr, **kwargs)

###################################################################################################
# calculate a sha256 hash of a file
def sha256sum(filename):
  h  = hashlib.sha256()
  b  = bytearray(64 * 1024)
  mv = memoryview(b)
  with open(filename, 'rb', buffering=0) as f:
    for n in iter(lambda : f.readinto(mv), 0):
      h.update(mv[:n])
  return h.hexdigest()

###################################################################################################
# filespec to various fields as per the extractor zeek script (/opt/zeek/share/zeek/site/extractor.zeek)
#   source-fuid-uid-time.ext
#   eg.
#       SSL-FTnzwn4hEPJi7BfzRk-CsRaviydrGyYROuX3-20190402105425.crt
#
# there are other extracted files that come from the mitre-attack/bzar scripts, they are formatted like this:
#   local fname = fmt("%s_%s%s", c$uid, f$id, subst_string(smb_name, "\\", "_"));
#
#   CR7X4q2hmcXKqP0vVj_F3jZ2VjYttqhKaGfh__172.16.1.8_C$_WINDOWS_sny4u_un1zbd94ytwj99hcymmsad7j54gr4wdskwnqs0ki252jdsrf763zsm531b.exe
#   └----------------┘ └---------------┘└------------------------------------------------------------------------------------------┘
#           UID              FID          subst_string(smb_name, "\\", "_"))
#
#   (see https://github.com/mitre-attack/bzar/blob/master/scripts/bzar_files.bro#L50)
def extracted_filespec_to_fields(filespec):
  baseFileSpec = os.path.basename(filespec)
  match = re.search(r'^(?P<source>.*)-(?P<fid>.*)-(?P<uid>.*)-(?P<time>\d+)\.(?P<ext>.*?)$', baseFileSpec)
  if match is not None:
    result = ExtractedFileNameParts(match.group('source'), match.group('fid'), match.group('uid'),
                                    time.mktime(datetime.strptime(match.group('time'), "%Y%m%d%H%M%S").timetuple()),
                                    match.group('ext'))
  else:
    match = re.search(r'^(?P<uid>[0-9a-zA-Z]+)_(?P<fid>[0-9a-zA-Z]+).+\.(?P<ext>.*?)$', baseFileSpec)
    if match is not None:
      result = ExtractedFileNameParts('MITRE', match.group('fid'), match.group('uid'), time.time(), match.group('ext'))
    else:
      result = ExtractedFileNameParts(None, None, None, time.time(), None)

  return result

###################################################################################################
# open a file and close it, updating its access time
def touch(filename):
  open(filename, 'a').close()
  os.utime(filename, None)

###################################################################################################
class AtomicInt:
  def __init__(self, value=0):
    self.val = RawValue('i', value)
    self.lock = Lock()

  def increment(self):
    with self.lock:
      self.val.value += 1
      return self.val.value

  def decrement(self):
    with self.lock:
      self.val.value -= 1
      return self.val.value

  def value(self):
    with self.lock:
      return self.val.value

###################################################################################################
class FileScanProvider(ABC):

  @staticmethod
  @abstractmethod
  def max_requests(cls):
    # returns the maximum number of concurrently open requests this type of provider can handle
    pass

  @staticmethod
  @abstractmethod
  def check_interval(cls):
    # returns the amount of seconds you should sleep between checking for results
    pass

  @abstractmethod
  def submit(self, fileName=None, block=False, timeout=0):
    # returns something that can be passed into check_result for checking the scan status
    pass

  @abstractmethod
  def check_result(self, submissionResponse):
    # returns AnalyzerResult based on submissionResponse
    pass

  @staticmethod
  @abstractmethod
  def format(cls, fileName, response):
    # returns result dict based on response (see FILE_SCAN_RESULT_* above)
    pass

###################################################################################################
# class for searching for a hash with a VirusTotal public API, handling rate limiting
class VirusTotalSearch(FileScanProvider):

  # ---------------------------------------------------------------------------------
  # constructor
  def __init__(self, apiKey, reqLimit=VTOT_MAX_REQS, reqLimitSec=VTOT_MAX_SEC):
    self.apiKey = apiKey
    self.lock = Lock()
    self.history = deque()
    self.reqLimit = reqLimit
    self.reqLimitSec = reqLimitSec

  @staticmethod
  def max_requests():
    return VTOT_MAX_REQS

  @staticmethod
  def check_interval():
    return VTOT_CHECK_INTERVAL

  # ---------------------------------------------------------------------------------
  # do a hash lookup against VirusTotal, respecting rate limiting
  # VirusTotalSearch does the request and gets the response immediately;
  # the subsequent call to check_result (using submit's response as input)
  # will always return "True" since the work has already been done
  def submit(self, fileName=None, block=False, timeout=None):
    if timeout is None:
      timeout = self.reqLimitSec+5

    allowed = False
    response = None

    # timeout only applies if block=True
    timeoutTime = int(time.time()) + timeout

    # while limit only repeats if block=True
    while (not allowed) and (response is None):

      with self.lock:
        # first make sure we haven't exceeded rate limits
        nowTime = int(time.time())

        if (len(self.history) < self.reqLimit):
          # we've done fewer than the allowed requests, so assume we're good to go
          self.history.append(nowTime + self.reqLimitSec)
          allowed = True

        elif (self.history[0] < nowTime):
          # we've done more than the allowed requests, but the oldest one is older than the window
          _ = self.history.popleft()
          self.history.append(nowTime + self.reqLimitSec)
          allowed = True

      if allowed:
        try:
          response = requests.get(VTOT_URL, params={ 'apikey': self.apiKey, 'resource': sha256sum(fileName) })
        except requests.exceptions.RequestException as e:
          # things are bad
          return None

      elif block and (nowTime < timeoutTime):
        # rate limited, wait for a bit and come around and try again
        time.sleep(1)

      else:
        break

    return response

  # ---------------------------------------------------------------------------------
  # see comment for VirusTotalSearch.submit, the work has already been done
  def check_result(self, submissionResponse):
    result = AnalyzerResult(finished=True)

    if submissionResponse is not None:
      try:
        result.success = submissionResponse.ok
      except:
        pass

      try:
        result.result = submissionResponse.json()
      except (ValueError, TypeError):
        result.success = False

    return result

  # ---------------------------------------------------------------------------------
  # static method for formatting the response JSON (from requests.get) as a dict
  @staticmethod
  def format(fileName, response):
    result = {FILE_SCAN_RESULT_FILE : fileName,
              FILE_SCAN_RESULT_ENGINES : 0,
              FILE_SCAN_RESULT_HITS : 0,
              FILE_SCAN_RESULT_MESSAGE : None,
              FILE_SCAN_RESULT_DESCRIPTION : None}

    if isinstance(response, AnalyzerResult):
      resp = response.result
    else:
      resp = response

    if isinstance(resp, str):
      try:
        resp = json.loads(resp)
      except (ValueError, TypeError):
        pass

    # see https://www.virustotal.com/en/documentation/public-api/
    if isinstance(resp, dict):
      if 'response_code' in resp:
        if (resp['response_code'] == VTOT_RESP_FOUND) and ('positives' in resp) and (resp['positives'] >0):
          result[FILE_SCAN_RESULT_HITS] = resp['positives']
          if ('scans' in resp):
            result[FILE_SCAN_RESULT_ENGINES] = len(resp['scans'])
            scans = {engine:resp['scans'][engine] for engine in resp['scans'] if ('detected' in resp['scans'][engine]) and (resp['scans'][engine]['detected'] == True)}
            hits = defaultdict(list)
            for k, v in scans.items():
              hits[v['result'] if 'result' in v else 'unknown'].append(k)
            if (len(hits) > 0):
              # short result is most common signature name
              result[FILE_SCAN_RESULT_MESSAGE] = max(hits, key= lambda x: len(set(hits[x])))
              # long result is list of the signature names and the engines which generated them
              result[FILE_SCAN_RESULT_DESCRIPTION] = ";".join([f"{k}<{','.join(v)}>" for k, v in hits.items()])
          else:
            # we were reported positives, but no no details
            result[FILE_SCAN_RESULT_MESSAGE] = "VirusTotal reported signature matches"
            if 'permalink' in resp:
              result[FILE_SCAN_RESULT_DESCRIPTION] = resp['permalink']
    else:
      # this shouldn't have happened after our checking above, so I guess just return the string
      # and let the caller deal with it
      result[FILE_SCAN_RESULT_MESSAGE] = "Invalid response"
      result[FILE_SCAN_RESULT_DESCRIPTION] = f"{resp}"

    return result

###################################################################################################
# class for scanning a file with Malass
class MalassScan(FileScanProvider):

  # ---------------------------------------------------------------------------------
  # constructor
  def __init__(self, host, port, reqLimit=MAL_MAX_REQS):
    self.host = host
    self.port = port
    self.reqLimit = reqLimit
    self.transactionIdToFilenameDict = defaultdict(str)
    self.scanningFilesCount = AtomicInt(value=0)

  @staticmethod
  def max_requests():
    return MAL_MAX_REQS

  @staticmethod
  def check_interval():
    return MAL_CHECK_INTERVAL

  # ---------------------------------------------------------------------------------
  # upload a file to scan with Malass, respecting rate limiting. return submitted transaction ID
  def submit(self, fileName=None, block=False, timeout=MAL_SUBMIT_TIMEOUT_SEC):
    submittedTransactionId = None
    allowed = False

    # timeout only applies if block=True
    timeoutTime = int(time.time()) + timeout

    # while limit only repeats if block=True
    while (not allowed) and (submittedTransactionId is None):

      # first make sure we haven't exceeded rate limits
      if (self.scanningFilesCount.increment() <= self.reqLimit):
        # we've got fewer than the allowed requests open, so we're good to go!
        allowed = True
      else:
        self.scanningFilesCount.decrement()

      if allowed:
        # submit the sample for scanning
        success, transactionId, httpResponsePage =  malass_client.upload_file_to_malass(fileName, self.host, self.port)
        if success:
          submittedTransactionId = transactionId
          self.transactionIdToFilenameDict[submittedTransactionId] = os.path.basename(fileName)

      elif block and (nowTime < timeoutTime):
        # rate limited, wait for a bit and come around and try again
        time.sleep(1)

      else:
        break

    return submittedTransactionId

  # ---------------------------------------------------------------------------------
  # check the status of a previously submitted file
  def check_result(self, transactionId):

    result = AnalyzerResult()

    # make a nice dictionary of this AV report
    summaryDict = dict()
    finishedAvsDict = dict()
    summaryDict['complete'] = False
    summaryDict['error'] = ""

    filename = self.transactionIdToFilenameDict[transactionId]

    try:
      success, errMsg, avSummaryStr = malass_client.query_av_summary_rpt(transactionId, filename, self.host, self.port)
      if success:

        # get body text
        body = BeautifulSoup(avSummaryStr, "html.parser").find("body")
        if body is not None:
          result.success = True

          lines = body.text.split('\n')

          # see if analysis is complete (look for termination string, then truncate the list starting at MAL_END_OF_TRANSACTION, inclusive)
          eotIndices = [i for i, s in enumerate(lines) if MAL_END_OF_TRANSACTION in s]
          summaryDict['complete'] = (len(eotIndices) > 0)
          if summaryDict['complete']:
            del lines[eotIndices[0]:]

          # take report name/value pairs (minus AV results) and insert them into summaryDict
          try:
            summaryDict.update(dict(map(str, x[1:].split('=')) for x in lines if x.startswith('#')))
          except (ValueError, TypeError) as e:
            summaryDict['error'] = f"Report parse error: {str(e)}"
            summaryDict['complete'] = True # avoid future lookups, abandon submission

          # take AV results in this report and merge them into summaryDict
          summaryDict['av'] = {}
          for vmLine in [x for x in lines if x.startswith('av_vm_')]:
            avDict = dict(map(str, x.split('=')) for x in vmLine.split(","))
            if ('av_vm_name' in avDict) and (len(avDict['av_vm_name']) > 0):
              summaryDict['av'][avDict['av_vm_name']] = avDict

          # merge any new av results in this response into the final finishedAvsDict
          for avName, avEntry in summaryDict['av'].items():
            if ('av_vm_num' in avEntry) and (avEntry['av_vm_num'].isnumeric()) and (not (int(avEntry['av_vm_num']) in finishedAvsDict)):
              finishedAvsDict[int(avEntry['av_vm_num'])] = avName

          # are we done?
          if summaryDict['complete']:

            # yes, we are done! let's make sure at least one AV scanned, and report an error if not
            if (len(finishedAvsDict) == 0) and (len(summaryDict['error']) == 0):
              summaryDict['error'] = f"No AVs scanned file sample ({transactionId}/{filename})"

        else:
          summaryDict['error'] = f"Summary report contained no body ({transactionId}/{filename})"
          summaryDict['complete'] = True # avoid future lookups, abandon submission

      else:
        summaryDict['error'] = f"Summary report was not generated: {errMsg} ({transactionId}/{filename})"
        summaryDict['complete'] = True # avoid future lookups, abandon submission

    finally:
      if (transactionId is not None) and summaryDict['complete']:
        # decrement scanning counter and remove trans->filename mapping if this scan is complete
        self.scanningFilesCount.decrement()
        self.transactionIdToFilenameDict.pop(transactionId, None)

    result.finished = summaryDict['complete']
    result.result = summaryDict

    return result

  # ---------------------------------------------------------------------------------
  # static method for formatting the response summaryDict (from check_result)
  @staticmethod
  def format(fileName, response):
    result = {FILE_SCAN_RESULT_FILE : fileName,
              FILE_SCAN_RESULT_ENGINES : 0,
              FILE_SCAN_RESULT_HITS : 0,
              FILE_SCAN_RESULT_MESSAGE : None,
              FILE_SCAN_RESULT_DESCRIPTION : None}

    if isinstance(response, AnalyzerResult):
      resp = response.result
    else:
      resp = response

    if isinstance(resp, dict) and ('av' in resp) and (len(resp['av']) > 0):
      hitAvs = {k : v for k, v in resp['av'].items() if ('contains_a_virus' in resp['av'][k]) and (resp['av'][k]['contains_a_virus'].lower() == "yes")}
      result[FILE_SCAN_RESULT_HITS] = len(hitAvs)
      result[FILE_SCAN_RESULT_ENGINES] = len(resp['av'])
      hits = defaultdict(list)
      for k, v in hitAvs.items():
        hits[v['virus_name'] if 'virus_name' in v else 'unknown'].append(k)
      if (len(hits) > 0):
        # short result is most common signature name
        result[FILE_SCAN_RESULT_MESSAGE] = max(hits, key= lambda x: len(set(hits[x])))
        # long result is list of the signature names and the engines which generated them
        result[FILE_SCAN_RESULT_DESCRIPTION] = ";".join([f"{k}<{','.join(v)}>" for k, v in hits.items()])

    else:
      result[FILE_SCAN_RESULT_MESSAGE] = "Error or invalid response"
      if isinstance(resp, dict) and ('error' in resp):
        result[FILE_SCAN_RESULT_DESCRIPTION] = f"{resp['error']}"
      else:
        result[FILE_SCAN_RESULT_DESCRIPTION] = f"{resp}"

    return result

###################################################################################################
# class for scanning a file with ClamAV
class ClamAVScan(FileScanProvider):

  # ---------------------------------------------------------------------------------
  # constructor
  def __init__(self, debug=False, verboseDebug=False, socketFileName=None):
    self.scanningFilesCount = AtomicInt(value=0)
    self.debug = debug
    self.verboseDebug = verboseDebug
    self.socketFileName = socketFileName

  @staticmethod
  def max_requests():
    return CLAM_MAX_REQS

  @staticmethod
  def check_interval():
    return CLAM_CHECK_INTERVAL

  # ---------------------------------------------------------------------------------
  # upload a file to scan with ClamAV, respecting rate limiting. return submitted transaction ID
  def submit(self, fileName=None, block=False, timeout=CLAM_SUBMIT_TIMEOUT_SEC):
    clamavResult = AnalyzerResult()
    allowed = False
    connected = False

    # timeout only applies if block=True
    timeoutTime = int(time.time()) + timeout

    # while limit only repeats if block=True
    while (not allowed) and (not clamavResult.finished):

      if not connected:
        if self.verboseDebug: eprint(f"{get_ident()}: ClamAV attempting connection")
        clamAv = clamd.ClamdUnixSocket(path=self.socketFileName) if self.socketFileName is not None else clamd.ClamdUnixSocket()
      try:
        clamAv.ping()
        connected = True
        if self.verboseDebug: eprint(f"{get_ident()}: ClamAV connected!")
      except Exception as e:
        connected = False
        if self.debug: eprint(f"{get_ident()}: ClamAV connection failed: {str(e)}")

      if connected:
        # first make sure we haven't exceeded rate limits
        if (self.scanningFilesCount.increment() <= CLAM_MAX_REQS):
          # we've got fewer than the allowed requests open, so we're good to go!
          allowed = True
        else:
          self.scanningFilesCount.decrement()

      if connected and allowed:
        try:
          if self.verboseDebug: eprint(f'{get_ident()} ClamAV scanning: {fileName}')
          clamavResult.result = clamAv.scan(fileName)
          if self.verboseDebug: eprint(f'{get_ident()} ClamAV scan result: {clamavResult.result}')
          clamavResult.success = (clamavResult.result is not None)
          clamavResult.finished = True
        except Exception as e:
          if clamavResult.result is None:
            clamavResult.result = str(e)
          if self.debug: eprint(f'{get_ident()} ClamAV scan error: {clamavResult.result}')
        finally:
          self.scanningFilesCount.decrement()

      elif block and (nowTime < timeoutTime):
        # rate limited, wait for a bit and come around and try again
        time.sleep(1)

      else:
        break

    return clamavResult

  # ---------------------------------------------------------------------------------
  # return the result of the previously scanned file
  def check_result(self, clamavResult):
    return clamavResult if isinstance(clamavResult, AnalyzerResult) else AnalyzerResult(finished=True, success=False, result=None)

  # ---------------------------------------------------------------------------------
  # static method for formatting the response summaryDict (from check_result)
  @staticmethod
  def format(fileName, response):
    result = {FILE_SCAN_RESULT_FILE : fileName,
              FILE_SCAN_RESULT_ENGINES : 1,
              FILE_SCAN_RESULT_HITS : 0,
              FILE_SCAN_RESULT_MESSAGE : None,
              FILE_SCAN_RESULT_DESCRIPTION : None}

    if isinstance(response, AnalyzerResult):
      resp = response.result
    else:
      resp = response

    if isinstance(resp, dict):
      hits = []
      for filename, resultTuple in resp.items():
        if (len(resultTuple) == 2) and (resultTuple[0] == CLAM_FOUND_KEY):
          hits.append(resultTuple[1])
      result[FILE_SCAN_RESULT_HITS] = len(hits)
      if (len(hits) > 0):
        cnt = Counter(hits)
        # short message is most common signature name
        result[FILE_SCAN_RESULT_MESSAGE] = cnt.most_common(1)[0][0]
        # long description is list of the signature names and the engines which generated them
        result[FILE_SCAN_RESULT_DESCRIPTION] = ";".join([f"{x}<{CLAM_ENGINE_ID}>" for x in hits])

    else:
      result[FILE_SCAN_RESULT_MESSAGE] = "Error or invalid response"
      if isinstance(resp, dict) and ('error' in resp):
        result[FILE_SCAN_RESULT_DESCRIPTION] = f"{resp['error']}"
      else:
        result[FILE_SCAN_RESULT_DESCRIPTION] = f"{resp}"

    return result