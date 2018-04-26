# $Id$
# 
# @rocks@
# Copyright (c) 2000 - 2010 The Regents of the University of California
# All rights reserved. Rocks(r) v5.4 www.rocksclusters.org
# https://github.com/Teradata/stacki/blob/master/LICENSE-ROCKS.txt
# @rocks@
#
# $Log$
# Revision 1.2  2010/09/07 23:52:55  bruno
# star power for gb
#
# Revision 1.1  2010/06/15 19:35:43  bruno
# commands to:
#  - manage public keys
#  - start/stop a service
#
#

import stack.commands


class Command(stack.commands.list.host.command):
	"""
	List the public keys for hosts.
	
	<arg optional='1' type='string' name='host' repeat='1'>
	Zero, one or more host names. If no host names are supplied,
	information for all hosts will be listed.
	</arg>
	"""

	def run(self, params, args):
		self.beginOutput()

		hosts = self.getHostnames(args)
		if not hosts:
			return

		for host in hosts:
			self.db.execute("""select id, public_key from
				public_keys where node = (select id from
				nodes where name = '%s') """ % host)
		
			for id, key in self.db.fetchall():
				i = 0	
				for line in key.split('\n'):
					if i == 0:
						self.addOutput(host, (id, line))
					else:
						self.addOutput('', (' ', line))
					i += 1

		self.endOutput(header=['host', 'id', 'public key'],
			trimOwner=False)

