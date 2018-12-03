# @copyright@
# Copyright (c) 2006 - 2018 Teradata
# All rights reserved. Stacki(r) v5.x stacki.com
# https://github.com/Teradata/stacki/blob/master/LICENSE.txt
# @copyright@
import paramiko
import socket
import stack.commands
import time

class Plugin(stack.commands.Plugin):

	SSH_PORT = 2200
	OFFSET   = 9

	def provides(self):
		return 'backend'

	def requires(self):
		return ['dhcp', 'autoyast']

	def connect(self, client, ip):
		# Retry connecting to backend till it succeeds
		while True:
			try:
				client.connect(ip, port=Plugin.SSH_PORT)
				return True
			except (paramiko.BadHostKeyException, paramiko.AuthenticationException,
				paramiko.SSHException, socket.error) as e:
				time.sleep(10)
				pass
		return False

	def run(self, backendObj):
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		if not self.connect(client, backendObj['ip']):
			print('Error - Unable to connect to %s via port %d' % \
				(backendObj['ip'], Plugin.SSH_PORT))
			return
		
		sftp = client.open_sftp()
		sftp.put('/tmp/BackendTest.py', '/tmp/BackendTest.py')
		sftp.close()

		stdin, stdout, stderr = client.exec_command('export LD_LIBRARY_PATH=/opt/stack/lib;' \
			'/opt/stack/bin/python3 /tmp/BackendTest.py')

		for line in stderr:
			print(line.strip())

		for idx,line in enumerate(stdout):
			print('%d. %s' % (idx + Plugin.OFFSET, line.strip()))

		client.close()
