# @copyright@
# Copyright (c) 2006 - 2018 Teradata
# All rights reserved. Stacki(r) v5.x stacki.com
# https://github.com/Teradata/stacki/blob/master/LICENSE.txt
# @copyright@
import shlex
import stack.commands
import time

class Plugin(stack.commands.Plugin):

	def provides(self):
		return 'bootaction'

	def requires(self):
		return ['backend']

	def parse_accesslog(self, line, backendObj):
		line_arr = shlex.split(line)
		ip = line_arr[0]

		if ip != backendObj['ip']:
			return

		profile_cgi = ''
		if len(line_arr) < 5:
			return
		
		HTTP_SUCCESS = '200'
		SET_BOOTACTION = 'params={\"action\":\"os\"}'
		profile_cgi = line_arr[5]

		if SET_BOOTACTION in profile_cgi and line_arr[6] == HTTP_SUCCESS:
			print('14. Frontend - Bootaction set to "os"')
			return True

		return False

	def run(self, backendObj):
		retVal = False

		with open("/var/log/apache2/ssl_access_log", "r") as file:
			file.seek(0, 2)

			while 1:
				where = file.tell()
				line  = file.readline()

				if not line:
					time.sleep(1)
					file.seek(where)
				else:
					retVal = self.parse_accesslog(line, backendObj)

				if retVal:
					break
