#!/opt/stack/bin/python3 -E
import os
import subprocess
import time

class BackendTest:

	PARTITION_XML = '/tmp/partition.xml'
	LUDICROUS_LOG = '/var/log/ludicrous-client-debug.log'
	NUM_RETRIES   = 10
	SLEEP_TIME    = 10

	def isEmptyFile(self, filepath):
		return os.stat(filepath).st_size == 0

	def output_state(self, state, flag):
		test_env = os.environ.copy()
		test_env["LD_LIBRARY_PATH"] = "/opt/stack/lib:" + test_env["LD_LIBRARY_PATH"]
		cmd = ['/opt/stack/bin/smq-publish', '-chealth', '-t300', \
			'{"systest":"%s","flag":"%s"}' % (state, str(flag))]
		subprocess.run(cmd, env=test_env)

	def check_autoyast_files(self):
		file_list = ['/tmp/profile/autoinst.xml', '/tmp/stack_site/__init__.py']
		#
		# Once SSH is available, the autoyast, stacki chapets should have
		# already been created
		#
		'''
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
		'''
		#for f in file_list:
		f = file_list[0]
		if self.isEmptyFile(f):
			self.output_state("AUTOINST_Present", False)
			print('Backend - %s profile file - Empty' % f)
		else:
			self.output_state("AUTOINST_Present", True)
			print('Backend - %s - Present' % f)

	def check_file_exists(self, path):
		i = 0

		while i < BackendTest.NUM_RETRIES: 
			if os.path.isfile(path):
				return True

			time.sleep(BackendTest.SLEEP_TIME)
			i = i + 1

		return False

	def check_pkg_install(self):
		i = 0

		while i < BackendTest.NUM_RETRIES:
			if not self.isEmptyFile(BackendTest.LUDICROUS_LOG):
				print('Backend - %s log file - Populated with' \
					' installed packages' % BackendTest.LUDICROUS_LOG)
				return

			time.sleep(BackendTest.SLEEP_TIME)
			i = i + 1

		print('Backend - %s log file is empty - Check if Ludicrous is okay' \
			% BackendTest.LUDICROUS_LOG)

	def check_ludicrous_started(self):
		if self.check_file_exists(BackendTest.LUDICROUS_LOG):
			print('Backend - Ludicrous Service - Started')
		else:
			print('Backend - Ludicrous Service - May not have' \
				' been started' % BackendTest.LUDICROUS_LOG)

	def check_partition(self):
		if self.check_file_exists(BackendTest.PARTITION_XML):
			print('Backend - %s - Present' % BackendTest.PARTITION_XML)
		else:
			print('Backend - %s - Not Present' % BackendTest.PARTITION_XML)

	def run(self):
		test_list = [self.check_autoyast_files, self.check_ludicrous_started,  \
				self.check_partition, self.check_pkg_install]

		for test in test_list:
			test()

b = BackendTest()
b.run()
