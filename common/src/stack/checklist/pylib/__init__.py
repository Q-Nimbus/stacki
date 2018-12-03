# @copyright@
# Copyright (c) 2006 - 2018 Teradata
# All rights reserved. Stacki(r) v5.x stacki.com
# https://github.com/Teradata/stacki/blob/master/LICENSE.txt
# @copyright@
from datetime import datetime
from enum import Enum

class Backend:
	"""
	Object that encapsulates all backend attributes relevant
	to monitor installation
	"""
	def __init__(self, hostName, installaction):
		self.hostName = hostName
		self.installaction = installaction
		self.ipList = []
		self.macList = []
		self.stateArr = []
		self.macAddr = None
		self.ipAddr  = None
		self.action = None
		self.kernel = None
		self.ramdisk = None
		self.ipIndex = 0

	def dumpBackend(self):
		print('########## Attributes of %s - Backend ###########' % self.hostName)
		print('ip addr = %s' % ','.join(self.ipList))
		print('mac = %s' % ','.join(self.macList))
		print('kernel = %s' % self.kernel)
		print('ramdisk = %s' % self.ramdisk)
		print('#####################')

	def addIpAndMac(self, ip, mac):
		self.ipList.append(ip)
		self.macList.append(mac)

	def getCurrentState(self):
		return self.stateArr[-1]

	def addState(self, state):
		self.stateArr.append(state)
		self.stateArr.sort(key=lambda x: x.stateInt)

class State(Enum):
	"""
	Enum that represents various installation stages.
	"""
	DHCPDISCOVER = 1
	DHCPOFFER = 2
	DHCPREQUEST = 3
	DHCPACK = 4
	TFTP_RRQ = 5
	VMLinuz_RRQ = 6
	Initrd_RRQ = 7
	Autoyast_Sent = 8
	SSH_Open = 9
	AUTOINST_Present = 10
	Ludicrous_Started = 11
	Ludicrous_Populated = 12
	Bootaction_OS = 13
	Reboot_Okay = 14

class StateMessage:
	"""
	Object that encapsulates system test message attributes
	"""
	def __init__(self, ipAddr, state, isError, time):
		self.ipAddr = ipAddr
		self.state = state
		self.isError = isError
		self.time = time

	def dumpState(self):
		print('########## Attributes of State Message ###########')
		print('Ip addr = %s' % self.ipAddr)
		print('State = %s' % self.state.name)
		print('IsError = %s', str(self.isError))
		print('Time = %s' % self.convertTimestamp())
		print('##################################################')

	def convertTimestamp(self):
		return datetime.utcfromtimestamp(self.time) \
			.strftime('%Y-%m-%d %H:%M:%S')
