#
# @SI_Copyright@
# @SI_Copyright@
#
#

import subprocess
import os

def attr2bool(s):
	if type(s) == type([]) and s:
		return 1

	if s and s.upper() in [ 'ALL', 'YES', 'Y', 'TRUE', '1' ]:
		return 1

	return 0


def sortDiskId(entry):
	try:
		key = entry['diskid']
		if not key:
			key = sys.maxint
	except:
		key = sys.maxint

	return key



def getHostDisks(nukedisks):
	#
	# create a dictionary for the attached currently configured 
	# storage. the format is:
	#
	#	disks = [{
	#		'device'	: 'sda',
	#		'diskid'	: 1,
	#		'part'		: [ 'sda1', 'sda2' ],
	#		'raid'		: [ 'md0', 'md1' ],
	# 		'lvm'		: [ 'volgrp01-var', 'volgrp02-export' ],
	# 		'nuke'		: 0
	#	}]
	#
	p = subprocess.Popen([ 'lsblk', '-lio', 'NAME,RM,RO,TYPE' ],
		stdin=subprocess.PIPE, stdout=subprocess.PIPE,
		stderr=subprocess.PIPE)
	out = p.communicate()[0]
	
	disks = []
	diskentry = None
	diskid = 1

	for l in out.split('\n'):
		# Ignore empty lines
		if not l.strip():
			continue

		#
		# Skip read-only and removable devices
		#
		arr = l.split()
		name = arr[0].strip()
		removable = arr[1].strip()
		readonly  = arr[2].strip()
		mediatype = arr[3].strip()

		if mediatype.startswith('raid'):
			#
			# md mediatypes can be 'raid0', 'raid1', etc. let's
			# just shorten it to 'raid'.
			#
			mediatype = 'raid'

		if removable == '1' or readonly == '1' or mediatype not in [ 'disk', 'part', 'raid', 'lvm' ]:
			continue

		if mediatype == 'disk':
			diskentry = None
			for disk in disks:
				if disk['device'] == name:
					diskentry = disk
					break

			if not diskentry:
				if nukedisks and (nukedisks[0] == '*' or name in nukedisks):
					nuke = 1
				else:
					nuke = 0

				disks.append({
					'device'	: name,
					'diskid'	: diskid,
					'part'		: [],
					'raid'		: [],
					'lvm'		: [],
					'nuke'		: nuke 
				})

				for disk in disks:
					if disk['device'] == name:
						diskentry = disk
						break

				diskid = diskid + 1
		else:
			if name not in diskentry[mediatype]:
				diskentry[mediatype].append(name)
		
	if disks:
		disks.sort(key = sortDiskId)

	return disks


def getHostMountpoint(host_fstab, uuid, label):
	for part in host_fstab:
		if part['device'] == 'UUID=%s' % uuid:
			return part['mountpoint']
		elif part['device'] == 'LABEL=%s' % label:
			return part['mountpoint']

	return None


def getDiskPartNumber(disk):
	partnumber = 0

	p = subprocess.Popen([ 'blkid', '-o', 'export',
		'-s', 'PART_ENTRY_NUMBER', '-p', '/dev/%s' % disk ],
		stdin=subprocess.PIPE, stdout=subprocess.PIPE,
		stderr=subprocess.PIPE)
	out = p.communicate()[0]

	#
	# the above should only return one line
	#
	arr = out.split('=')

	if len(arr) == 2:
		partnumber = arr[1].strip()

	return partnumber


def getHostPartitions(disks, host_fstab):
	partitions = []

	for d in disks:
		disk = d['device']
	
		p = subprocess.Popen([ 'lsblk', '-nrbo', 
			'NAME,SIZE,UUID,LABEL,MOUNTPOINT,FSTYPE',
			'/dev/%s' % disk ],
			stdin=subprocess.PIPE, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE)
		out = p.communicate()[0]
		
		for l in out.split('\n'):
			# Ignore empty lines
			if not l.strip():
				continue

			arr = l.split(' ')

			#
			# ignore the "whole" disk device (we are interested
			# only in partitions)
			#
			diskname = arr[0]
			if diskname == disk:
				continue

			try:
				size = int(int(arr[1]) / (1024 * 1024))
			except:
				size = 0

			uuid = arr[2]
			label = arr[3]
			mountpoint = arr[4]
			fstype = arr[5]

			if not mountpoint:
				mountpoint = getHostMountpoint(host_fstab,
					uuid, label)

			if mountpoint == '[SWAP]':
				mountpoint = 'swap'

			partnumber = getDiskPartNumber(diskname)

			disk_partitions = {}
			disk_partitions['device'] = disk
			disk_partitions['mountpoint'] = mountpoint
			disk_partitions['size'] = size
			disk_partitions['fstype'] = fstype
			disk_partitions['uuid'] = uuid
			disk_partitions['diskpart'] = diskname

			if partnumber:
				disk_partitions['partnumber'] = partnumber

			if label:
				disk_partitions['options'] = \
					'--label=%s' % label
			else:
				disk_partitions['options'] = ''

			partitions.append(disk_partitions)

	return partitions


def getHostFstab(devices):
	import tempfile

	host_fstab = []

	mountpoint = tempfile.mktemp()
	os.makedirs(mountpoint)
	fstab = mountpoint + '/etc/fstab'

	for device in devices:
		os.system('mount %s %s' % (device, mountpoint) + \
			' > /dev/null 2>&1')

		if os.path.exists(fstab):
			file = open(fstab)

			for line in file.readlines():
				entry = {}

				l = line.split()
				if len(l) < 3:
					continue

				if l[0][0] == '#':
					continue

				entry['device'] = l[0].strip()
				entry['mountpoint'] = l[1].strip()
				entry['fstype'] = l[2].strip()

				host_fstab.append(entry)

			file.close()

		os.system('umount %s 2> /dev/null' % (mountpoint))

		if host_fstab:
			break

	try:
		os.removedirs(mountpoint)
	except:
		pass

	return host_fstab

