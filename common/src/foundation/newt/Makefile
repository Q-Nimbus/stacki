# @copyright@
# Copyright (c) 2006 - 2018 Teradata
# All rights reserved. Stacki(r) v5.x stacki.com
# https://github.com/Teradata/stacki/blob/master/LICENSE.txt
# @copyright@

PKGROOT		= /opt/stack
ROLLROOT	= ../../../..
DEPENDS.FILES	= newt-$(VERSION).tar.gz

include $(STACKBUILD)/etc/CCRules.mk

BOOTSTRAP = slang-devel popt-devel

bootstrap:
	$(STACKBUILD)/bin/package-install $(BOOTSTRAP)
	$(MAKE) install-rpm

build:
	tar -xzf newt-$(VERSION).tar.gz
	( 								\
		cd newt-$(VERSION);					\
		./configure --prefix=$(PKGROOT); 			\
		PATH=/bin:/usr/bin:$(PKGROOT)/bin;			\
		$(MAKE) PYTHONVERS=$(PY.LIB);				\
	)

install::
	mkdir -p $(ROOT)/$(PKGROOT)
	(								\
		cd newt-$(VERSION);					\
		PATH=/bin:/usr/bin:$(PKGROOT)/bin;			\
		$(MAKE) PYTHONVERS=$(PY.LIB) install DESTDIR=$(ROOT);	\
	)

clean::
	rm -rf newt-$(VERSION)
