# @copyright@
# Copyright (c) 2006 - 2018 Teradata
# All rights reserved. Stacki(r) v5.x stacki.com
# https://github.com/Teradata/stacki/blob/master/LICENSE.txt
# @copyright@
import stack.commands
import time

class Plugin(stack.commands.Plugin):

	dhcp_status = ['DHCPDISCOVER', 'DHCPOFFER', 'DHCPREQUEST', 'DHCPACK']

	def provides(self):
		return 'dhcp'

	def process_dhcp(self, line, backendObj):
		line_arr = line.split()
		daemon_name = line_arr[2]

		if 'dhcpd' not in daemon_name:
			return

		msg_type = line_arr[3]

		if msg_type == Plugin.dhcp_status[self.dhcp_status_index]:

			if msg_type == 'DHCPDISCOVER':
				mac = line_arr[5]
				interface = line_arr[7]

				if mac in backendObj['mac']:
					self.dhcp_status_index = self.dhcp_status_index + 1
					dhcp_start = time.time()
					print('1. Frontend - DHCPDISCOVER - Received')
					return

			elif msg_type == 'DHCPOFFER':
				ip   = line_arr[5]
				mac  = line_arr[7]
	
				if ip in backendObj['ip'] and mac in backendObj['mac']:
					self.dhcp_status_index = self.dhcp_status_index + 1
					print('2. Frontend - DHCPOFFER - Received')
					return

			elif msg_type == 'DHCPREQUEST':
				ip = line_arr[5]
				mac = line_arr[8]

				if ip in backendObj['ip'] and mac in backendObj['mac']:
					self.dhcp_status_index = self.dhcp_status_index + 1
					print('3. Frontend - DHCPREQUEST - Received')
					return

			elif msg_type == 'DHCPACK':
				ip  = line_arr[5]
				mac = line_arr[7]

				if ip in backendObj['ip'] and mac in backendObj['mac']:
					self.dhcp_status_index = self.dhcp_status_index + 1
					self.status_arr_index = self.status_arr_index + 1
					print('4. Frontend - DHCPACK - Received')
					#
					# Set the IP, MAC of backend based on DHCPACK
					# For easr of processing later.
					#
					self.owner.dictObj['ip'] = ip
					self.owner.dictObj['mac'] = mac
					return

	def process_tftp(self, line, backendObj):
		line_arr = line.split()
		daemon_name = line_arr[2]

		if 'tftp' not in daemon_name:
			return

		ip = line_arr[5]
		pxe_file = line_arr[7]

		if ip != backendObj['ip']:
			return

		if '/' in pxe_file:
			pxe_arr = pxe_file.split('/')
			hexip = pxe_arr[1]
			backend_ip_arr = backendObj['ip'].split('.')
			backend_hex_ip = '{:02X}{:02X}{:02X}{:02X}'.format(*map(int, backend_ip_arr))

			if backend_hex_ip == pxe_arr[1]:
				print('5. Frontend - TFTP read file request - Received')
				self.tftp_status_index = self.tftp_status_index + 1
				return

		if self.tftp_status_index == 1 and pxe_file == backendObj['kernel']:
			print('6. Frontend - VMLinuz read file request - Received')
			self.tftp_status_index = self.tftp_status_index + 1
			return

		if self.tftp_status_index == 2 and pxe_file == backendObj['ramdisk']:
			print('7. Frontend - Initrd read file request - Received')
			self.tftp_status_index = self.tftp_status_index + 1
			self.status_arr_index = self.status_arr_index + 1
			return

	def run(self, backendObj):
		self.dhcp_status_index = 0
		self.dhcp_start = 0

		self.tftp_status_index = 0
		tftp_status = ['RRQ PXE file', 'RRQ VMLinuz', 'RRQ InitRD']

		status_arr = [self.process_dhcp, self.process_tftp]
		self.status_arr_index = 0

		with open("/var/log/messages", "r") as file:
			file.seek(0, 2)

			while 1:

				if self.status_arr_index == len(status_arr):
					break

				where = file.tell()
				line  = file.readline()

				if not line:
					time.sleep(1)
					file.seek(where)
				else:
					status_arr[self.status_arr_index](line, backendObj)
