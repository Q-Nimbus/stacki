import logging
import queue
import socket
from stack.checklist import Backend, State, StateMessage
from stack.checklist.threads import MQProcessor, LogParser, BackendExec
import stack.commands
from stack.exception import ArgRequired, ArgUnique, CommandError
import sys
import time
import zmq

time_dict={}

def measureTime(msg, limit):

	def timeit(method):

		def timed(*args, **kwargs):
			start = time.time()
			method(*args, **kwargs)
			end = time.time()

			elapsed = end - start
			method_name = method.__name__
			global time_dict

			if method_name in time_dict:
				time_dict[method_name] = time_dict[method_name] + elapsed
			else:
				time_dict[method_name] = elapsed
	
			if time_dict[method_name] > limit:
				print('!!! %s !!!' % msg)
		return timed

	return timeit

class Command(stack.commands.Command, stack.commands.HostArgumentProcessor):
	
	def dumpObj(self):
		print('#####################')
		print('ip addr = %s' % ','.join(self.dictObj['ip']))
		print('mac = %s' % ','.join(self.dictObj['mac']))
		print('#####################')

	def enrichBackends(self, args):
		hnameBackendMap = {}

		hosts = self.getHostnames(args)

		if len(args) == 0:
			raise ArgRequired(self, 'hostname')

		op = self.call('list.host', args)
		if not op:
			raise ArgRequired(self, 'host')

		backendList = []
	
		for o in op:
			b = Backend(o['host'], o['installaction'])
			hnameBackendMap[o['host']] = b
			backendList.append(b)

		op = self.call('list.network', ['pxe=True'])
		pxe_network_list = []
		for o in op:
			pxe_network_list.append(o['network'])

		self.ipBackendMap = {}
		ip_list  = []
		mac_list = []
		op = self.call('list.host.interface', args)
		for o in op:
			hostname = o['host']

			if o['network'] in pxe_network_list:
				b = hnameBackendMap[hostname]
				b.addIpAndMac(o['ip'], o['mac'])
				if o['ip']:
					self.ipBackendMap[o['ip']] = b

		op = self.call('list.host.boot', args)
		for o in op:
			hostname = o['host']
			action = o['action']
			b = hnameBackendMap[hostname]
			b.action = o['action']

		# Build a bootaction dictionary for ease of access
		bootactionMap = {}
		op = self.call('list.bootaction', \
			['bootaction=%s' % b.installaction, 'type=%s' % b.action])
		for o in op:
			key = o['bootaction'] + '-' + o['type']
			bootactionMap[key] = o

		for b in backendList:
			key = b.installaction + '-' + b.action
			o = bootactionMap[key]
			b.kernel  = o['kernel']
			b.ramdisk = o['ramdisk']

	def processQueueMsgs(self):
		while True:
			sm = self.queue.get()
			stateList = self.ipBackendMap[sm.ipAddr].stateArr
			stateList.append(sm)

			# Lazy init backend Exec thread
			if sm.state == State.DHCPACK and not sm.isError \
				and sm.ipAddr not in self.ipThreadMap:
				backendThread = BackendExec(sm.ipAddr, self.queue)
				self.ipThreadMap[sm.ipAddr] = backendThread
				backendThread.start()

			print('\n #### STATE LIST BEGINS - HOST %s ####' % sm.ipAddr)
			for s in stateList:
				print('%s State = %s, isError = %s' % \
					(s.convertTimestamp(), s.state, s.isError))
			print('#### STATE LIST ENDS - HOST %s ####' % sm.ipAddr)
			sys.stdout.flush()
	
	def run(self, params, args):
		self.ipBackendMap = {}
		self.enrichBackends(args)

		self.queue = queue.Queue()
		dhcpLog = LogParser("/var/log/messages", self.ipBackendMap, self.queue)
		dhcpLog.setDaemon(True)
		dhcpLog.start()

		apacheLog = LogParser("/var/log/apache2/ssl_access_log", self.ipBackendMap, self.queue)
		apacheLog.setDaemon(True)
		apacheLog.start()

		context = zmq.Context()
		tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		mqSubscriber = MQProcessor(context, tx, self.ipBackendMap.keys(), self.queue)
		
		mqSubscriber.setDaemon(True)
		mqSubscriber.start()

		self.ipThreadMap = {}
		self.processQueueMsgs()	
