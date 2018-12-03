# @copyright@
# Copyright (c) 2006 - 2018 Teradata
# All rights reserved. Stacki(r) v5.x stacki.com
# https://github.com/Teradata/stacki/blob/master/LICENSE.txt
# @copyright@
import logging
import paramiko
import socket
import shlex
from stack.checklist import State, StateMessage
import stack.mq.processors
import time
import threading
import queue

class LogParser(threading.Thread):
	"""
	Parses log messages and appends those relevant to system
	installation to the shared queue.
	"""
	def __init__(self, path, ipBackendMap, queue):
		super(self.__class__, self).__init__()
		self.path = path
		self.ipBackendMap = ipBackendMap
		self.queue = queue
		self.parseFunc = self.parse_apachelog

		if '/var/log/messages' in path:
			self.parseFunc = self.parse_varlog

	def findMac(self, mac):
		backendList = self.ipBackendMap.values()
		for b in backendList:
			if mac in b.macList:
				b.ipIndex = b.macList.index(mac)
				return b
		return None

	def process_dhcpd(self, line):
		line_arr = line.split()
		msg_type = line_arr[3]

		if msg_type == 'DHCPDISCOVER':
			mac = line_arr[5]
			interface = line_arr[7]
			backend = self.findMac(mac)

			if not backend:
				return

			sm = StateMessage(backend.ipList[0], State.DHCPDISCOVER,\
				 False, time.time())
			self.queue.put(sm)

		elif msg_type in ['DHCPOFFER']:
			ip   = line_arr[5]
			mac  = line_arr[7]

			if ip in self.ipBackendMap:
				backend = self.ipBackendMap[ip]
				if mac == backend.macList[0]:
					sm = StateMessage(ip, State.DHCPOFFER, \
						False, time.time())
					self.queue.put(sm)

		elif msg_type == 'DHCPREQUEST':
			ip = line_arr[5]
			mac = line_arr[8]

			if ip in self.ipBackendMap:
				backend = self.ipBackendMap[ip]
				if mac == backend.macList[0]:
					sm = StateMessage(ip, State.DHCPREQUEST, \
						False, time.time())
					self.queue.put(sm)
		elif msg_type == 'DHCPACK':
			ip  = line_arr[5]
			mac = line_arr[7]

			if ip in self.ipBackendMap:
				backend = self.ipBackendMap[ip]
				if mac == backend.macList[0]:
					sm = StateMessage(ip, State.DHCPACK, \
						False, time.time())
					self.queue.put(sm)

	def process_tftp(self, line):
		line_arr = line.split()
		ip = line_arr[5]
		pxe_file = line_arr[7]

		if ip not in  self.ipBackendMap:
			return

		backend = self.ipBackendMap[ip]

		if '/' in pxe_file:
			pxe_arr = pxe_file.split('/')
			hexip = pxe_arr[1]
			backend_ip_arr = backend.ipList[0].split('.')
			backend_hex_ip = '{:02X}{:02X}{:02X}{:02X}'.format(*map(int, backend_ip_arr))

			if backend_hex_ip == pxe_arr[1]:
				sm = StateMessage(ip, State.TFTP_RRQ, False, time.time())
				self.queue.put(sm)
				return

		if pxe_file == backend.kernel:
			sm = StateMessage(ip, State.VMLinuz_RRQ, False, time.time())
			self.queue.put(sm)
			return

		if pxe_file == backend.ramdisk:
			sm = StateMessage(ip, State.Initrd_RRQ, False, time.time())
			self.queue.put(sm)
			return

	def parse_apachelog(self, line):
		line_arr = shlex.split(line)
		ip = line_arr[0]

		if len(line_arr) < 5 or ip not in self.ipBackendMap:
			return

		backend = self.ipBackendMap[ip]
		profile_cgi = line_arr[5]
		HTTP_SUCCESS = '200'

		if '/install/sbin/profile.cgi' in profile_cgi and line_arr[6] == HTTP_SUCCESS:
			sm = StateMessage(ip, State.Autoyast_Sent, False, time.time())
			self.queue.put(sm)
		return

	def parse_varlog(self, line):
		line_arr = line.split()
		daemon_name = line_arr[2].replace(':', '')

		if 'dhcpd' in daemon_name:
			self.process_dhcpd(line)
		elif 'tftpd' in daemon_name:
			self.process_tftp(line)
		else:
			return

		msg_type = line_arr[3]

	def run(self):
		with open(self.path, "r") as file:
			file.seek(0, 2)

			while 1:
				where = file.tell()
				line  = file.readline()

				if not line:
					time.sleep(1)
					file.seek(where)
				else:
					self.parseFunc(line)

class BackendExec(threading.Thread):
	"""
	Runs scripts / tests on a Backend via SSH and appends
	State messages to the queue about the installation
	progress.
	"""

	SSH_PORT    = 2200
	MAX_RETRIES = 25

	def __init__(self, ip, queue):
		super(self.__class__, self).__init__()
		self.ip = ip
		self.queue = queue
		self.log = logging.getLogger("Backend-Exec")
		logging.basicConfig(filename='/var/log/Backend-Exec-%s.log' % ip,
			filemode='w+', level=logging.INFO)

	def connect(self, client):
		num_tries = 0

		# Retry connecting to backend till it succeeds
		while num_tries <= BackendExec.MAX_RETRIES:
			try:
				num_tries = num_tries + 1
				client.connect(self.ip, port=BackendExec.SSH_PORT)
				return True
			except (paramiko.BadHostKeyException, paramiko.AuthenticationException,
				paramiko.SSHException, socket.error) as e:
				time.sleep(10)
				pass
		return False

	def run(self):
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

		if not self.connect(client):
			log.warn('Error - Unable to connect to %s via port %d' % \
				(self.ip, BackendExec.SSH_PORT))
			client.close()
			sm = StateMessage(self.ip, State.SSH_Open, True, time.time())
			self.queue.put(sm)
			return

		self.log.debug('Connected to backend %s via port 2200' % self.ip)
		sm = StateMessage(self.ip, State.SSH_Open, False, time.time())
		self.queue.put(sm)

		sftp = client.open_sftp()
		sftp.put('/tmp/BackendTest.py', '/tmp/BackendTest.py')
		sftp.close()

		stdin, stdout, stderr = client.exec_command('export LD_LIBRARY_PATH=/opt/stack/lib;' \
			'/opt/stack/bin/python3 /tmp/BackendTest.py')

		for line in stderr:
			log.error(line.strip())

		client.close()

class MQProcessor(stack.mq.processors.ProcessorBase):
	"""
	Listens for messages about Backend installation and
	appends State Messages to message queue
	"""

	def isActive(self):
		return True

	def channel(self):
		return 'health'

	def __init__(self, context, sock, ipList, queue):
		stack.mq.processors.ProcessorBase.__init__(self, context, sock)
		self.ipList = ipList
		self.queue = queue

		self.log = logging.getLogger("MQProcessor")
		logging.basicConfig(filename='/var/log/MQProcessor.log', filemode='w+', level=logging.INFO)

	def process(self, message):
		header = message.getTime()
		source = message.getSource()
		payload = message.getPayload()

		self.log.debug('Paylod = %s ' % str(payload))

		try:
			if source not in self.ipList:
				return

			o = json.loads(payload)
			sm = StateMessage(source, State[o['systest_state']], False, time.time())
			self.queue.put(sm)
		except:
			self.log.warn('JSON parse error %s' % o)
